use chrono::Local;
use std::fs::{OpenOptions, create_dir_all};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{Emitter, Manager};

struct BackendState(Mutex<Option<Child>>);
const BACKEND_EXE_NAME: &str = "local_v_backend.exe";
const LOG_FILE_APP: &str = "app.log";
const LOG_FILE_BACKEND: &str = "backend.log";
const LOG_FILE_FRONTEND: &str = "frontend.log";
const LOG_MAX_BYTES: u64 = 10 * 1024 * 1024;
const LOG_BACKUP_COUNT: usize = 5;

fn timestamp() -> String {
  Local::now().format("%Y-%m-%d %H:%M:%S").to_string()
}

fn ensure_logs_dir(app: &tauri::AppHandle) -> Result<PathBuf, String> {
  let app_data_dir = app
    .path()
    .app_data_dir()
    .map_err(|error| format!("获取 appData 目录失败: {}", error))?;
  let logs_dir = app_data_dir.join("logs");
  create_dir_all(&logs_dir).map_err(|error| {
    format!(
      "创建日志目录失败 {}: {}",
      logs_dir.display(),
      error
    )
  })?;
  Ok(logs_dir)
}

fn append_log_line(path: &Path, line: &str) -> Result<(), String> {
  rotate_log_file(path)?;
  let mut file = OpenOptions::new()
    .create(true)
    .append(true)
    .open(path)
    .map_err(|error| format!("打开日志文件失败 {}: {}", path.display(), error))?;
  writeln!(file, "{}", line)
    .map_err(|error| format!("写入日志文件失败 {}: {}", path.display(), error))
}

fn rotate_log_file(path: &Path) -> Result<(), String> {
  let current_size = match std::fs::metadata(path) {
    Ok(meta) => meta.len(),
    Err(_) => return Ok(()),
  };

  if current_size < LOG_MAX_BYTES {
    return Ok(());
  }

  for index in (1..=LOG_BACKUP_COUNT).rev() {
    let source = if index == 1 {
      path.to_path_buf()
    } else {
      PathBuf::from(format!("{}.{}", path.display(), index - 1))
    };
    let target = PathBuf::from(format!("{}.{}", path.display(), index));

    if !source.exists() {
      continue;
    }

    if target.exists() {
      let _ = std::fs::remove_file(&target);
    }

    std::fs::rename(&source, &target).map_err(|error| {
      format!(
        "日志轮转失败 {} -> {}: {}",
        source.display(),
        target.display(),
        error
      )
    })?;
  }

  Ok(())
}

fn write_app_log(app: &tauri::AppHandle, level: &str, message: &str) {
  if let Ok(logs_dir) = ensure_logs_dir(app) {
    let line = format!("[{}][{}] {}", timestamp(), level, message);
    let _ = append_log_line(&logs_dir.join(LOG_FILE_APP), &line);
  }
}

#[tauri::command]
fn append_frontend_log(
  app: tauri::AppHandle,
  level: Option<String>,
  message: String,
) -> Result<(), String> {
  let logs_dir = ensure_logs_dir(&app)?;
  let level = level.unwrap_or_else(|| "INFO".to_string()).to_uppercase();
  let line = format!("[{}][{}] {}", timestamp(), level, message);
  append_log_line(&logs_dir.join(LOG_FILE_FRONTEND), &line)
}

fn backend_candidates(app: &tauri::AppHandle) -> Vec<PathBuf> {
  let mut candidates: Vec<PathBuf> = Vec::new();

  if cfg!(debug_assertions) {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    candidates.push(manifest_dir.join("resources").join(BACKEND_EXE_NAME));
  }

  if let Ok(resource_dir) = app.path().resource_dir() {
    candidates.push(resource_dir.join(BACKEND_EXE_NAME));
    candidates.push(resource_dir.join("resources").join(BACKEND_EXE_NAME));
  }

  // Also check the current exe directory as a fallback
  if let Ok(current_exe) = std::env::current_exe() {
    if let Some(exe_dir) = current_exe.parent() {
      candidates.push(exe_dir.join(BACKEND_EXE_NAME));
      candidates.push(exe_dir.join("resources").join(BACKEND_EXE_NAME));
    }
  }

  candidates
}

fn start_backend(app: &tauri::AppHandle) -> Result<Child, String> {
  let candidates = backend_candidates(app);
  let exe_path = candidates
    .iter()
    .find(|path| path.exists())
    .cloned()
    .ok_or_else(|| {
      let checked = candidates
        .iter()
        .map(|path| path.display().to_string())
        .collect::<Vec<String>>()
        .join("\n  ");
      let message = format!("后端服务未找到。已检查以下位置:\n  {}\n\n请确保已运行 'npm run backend:build' 打包后端。", checked);
      message
    })?;

  // Protect against accidental self-spawn recursion.
  if let Ok(current_exe) = std::env::current_exe() {
    if current_exe == exe_path {
      return Err(format!(
        "后端路径与主程序相同，已阻止递归启动: {}",
        exe_path.display()
      ));
    }
  }

  let mut command = Command::new(&exe_path);
  if cfg!(debug_assertions) {
    // In development, keep backend logs visible in the terminal.
    command.stdout(Stdio::inherit());
    command.stderr(Stdio::inherit());
  } else {
    let logs_dir = ensure_logs_dir(app)?;
    let backend_log_path = logs_dir.join(LOG_FILE_BACKEND);
    rotate_log_file(&backend_log_path)?;
    let stdout_file = OpenOptions::new()
      .create(true)
      .append(true)
      .open(&backend_log_path)
      .map_err(|error| format!("打开后端日志失败 {}: {}", backend_log_path.display(), error))?;
    let stderr_file = stdout_file
      .try_clone()
      .map_err(|error| format!("复制后端日志句柄失败: {}", error))?;
    command.stdout(Stdio::from(stdout_file));
    command.stderr(Stdio::from(stderr_file));
  }

  if let Ok(app_data_dir) = app.path().app_data_dir() {
    let config_path = app_data_dir.join("video_folder.json");
    command.env("LOCAL_V_CONFIG_PATH", config_path);
  }

  let child = command
    .spawn()
    .map_err(|error| {
      let message = format!("启动后端失败 {}: {}", exe_path.display(), error);
      message
    })?;

  write_app_log(app, "INFO", &format!("后端已启动: {}", exe_path.display()));
  Ok(child)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![append_frontend_log])
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .setup(|app| {
      app.manage(BackendState(Mutex::new(None)));
      write_app_log(app.handle(), "INFO", "主程序启动");

      // Try to start backend with retry logic
      let mut backend_started = false;
      let mut last_error = String::new();
      
      for attempt in 1..=3 {
        match start_backend(app.handle()) {
          Ok(child) => {
            let state = app.state::<BackendState>();
            if let Ok(mut guard) = state.0.lock() {
              *guard = Some(child);
            }
            backend_started = true;
            write_app_log(app.handle(), "INFO", &format!("后端第 {} 次尝试启动成功", attempt));
            break;
          }
          Err(message) => {
            last_error = message;
            write_app_log(
              app.handle(),
              "WARN",
              &format!("后端第 {} 次尝试启动失败: {}", attempt, last_error),
            );
            if attempt < 3 {
              std::thread::sleep(std::time::Duration::from_millis(500 * attempt));
            }
          }
        }
      }
      
      if !backend_started {
        write_app_log(
          app.handle(),
          "ERROR",
          &format!("后端启动失败，已重试 3 次: {}", last_error),
        );
        // Only emit error event if we have a window
        if let Some(win) = app.get_webview_window("main") {
          let _ = win.emit("backend-error", last_error);
        }
      }

      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .on_window_event(|window, event| {
      if let tauri::WindowEvent::CloseRequested { .. } = event {
        let app_handle = window.app_handle();
        {
          let state = app_handle.state::<BackendState>();
          let mut guard = match state.0.lock() {
            Ok(guard) => guard,
            Err(_) => return,
          };
          if let Some(mut child) = guard.take() {
            let _ = child.kill();
            write_app_log(&app_handle, "INFO", "窗口关闭，已停止后端进程");
          }
        }
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

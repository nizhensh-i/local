use chrono::Local;
use std::collections::HashSet;
use std::fs::{OpenOptions, create_dir_all, read_to_string, remove_file};
use std::io::Write;
use std::net::TcpListener;
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread::sleep;
use std::time::Duration;
use tauri::{Emitter, Manager};

struct BackendState(Mutex<Option<Child>>);
const BACKEND_EXE_NAME: &str = "local_v_backend.exe";
const BACKEND_PID_FILE: &str = "backend.pid";
const BACKEND_PORT: u16 = 56173;
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

fn backend_pid_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
  let app_data_dir = app
    .path()
    .app_data_dir()
    .map_err(|error| format!("获取 appData 目录失败: {}", error))?;
  create_dir_all(&app_data_dir)
    .map_err(|error| format!("创建 appData 目录失败 {}: {}", app_data_dir.display(), error))?;
  Ok(app_data_dir.join(BACKEND_PID_FILE))
}

fn store_backend_pid(app: &tauri::AppHandle, pid: u32) {
  if let Ok(path) = backend_pid_path(app) {
    let _ = std::fs::write(&path, pid.to_string());
  }
}

fn clear_backend_pid(app: &tauri::AppHandle) {
  if let Ok(path) = backend_pid_path(app) {
    let _ = remove_file(path);
  }
}

fn is_backend_port_available() -> bool {
  TcpListener::bind(("127.0.0.1", BACKEND_PORT)).is_ok()
}

fn kill_process_by_pid(pid: u32) -> Result<(), String> {
  #[cfg(target_os = "windows")]
  {
    let status = Command::new("taskkill")
      .args(["/PID", &pid.to_string(), "/T", "/F"])
      .status()
      .map_err(|error| format!("结束残留进程失败: {}", error))?;

    if status.success() {
      return Ok(());
    }

    return Err(format!("结束残留进程失败，退出码: {}", status));
  }

  #[cfg(not(target_os = "windows"))]
  {
    let status = Command::new("kill")
      .args(["-TERM", &pid.to_string()])
      .status()
      .map_err(|error| format!("结束残留进程失败: {}", error))?;

    if status.success() {
      return Ok(());
    }

    Err(format!("结束残留进程失败，退出码: {}", status))
  }
}

fn wait_for_child_exit(child: &mut Child, timeout_ms: u64) -> Result<bool, String> {
  let attempts = (timeout_ms / 100).max(1);
  for _ in 0..attempts {
    match child.try_wait() {
      Ok(Some(_)) => return Ok(true),
      Ok(None) => sleep(Duration::from_millis(100)),
      Err(error) => return Err(format!("检查后端进程退出状态失败: {}", error)),
    }
  }

  Ok(false)
}

fn backend_pids_on_port(port: u16) -> Vec<u32> {
  #[cfg(target_os = "windows")]
  {
    let output = Command::new("netstat")
      .args(["-ano", "-p", "tcp"])
      .output();

    let Ok(output) = output else {
      return Vec::new();
    };

    let needle = format!(":{}", port);
    let mut pids = HashSet::new();

    for line in String::from_utf8_lossy(&output.stdout).lines() {
      let columns: Vec<&str> = line.split_whitespace().collect();
      if columns.len() < 5 {
        continue;
      }

      if !columns[0].to_ascii_uppercase().starts_with("TCP") {
        continue;
      }

      // Match local-address column instead of localized LISTENING state text.
      if !columns[1].contains(&needle) {
        continue;
      }

      if let Ok(pid) = columns[4].parse::<u32>() {
        if pid > 0 {
          pids.insert(pid);
        }
      }
    }

    return pids.into_iter().collect();
  }

  #[cfg(not(target_os = "windows"))]
  {
    let output = Command::new("lsof")
      .args([
        "-nP",
        &format!("-iTCP:{}", port),
        "-sTCP:LISTEN",
        "-t",
      ])
      .output();

    let Ok(output) = output else {
      return Vec::new();
    };

    let mut pids = HashSet::new();
    for line in String::from_utf8_lossy(&output.stdout).lines() {
      if let Ok(pid) = line.trim().parse::<u32>() {
        if pid > 0 {
          pids.insert(pid);
        }
      }
    }

    pids.into_iter().collect()
  }
}

fn cleanup_backend_port_occupants(app: &tauri::AppHandle, reason: &str) {
  let current_pid = std::process::id();
  let pids = backend_pids_on_port(BACKEND_PORT);

  if pids.is_empty() {
    return;
  }

  let mut killed = 0_u32;
  for pid in pids {
    if pid == current_pid {
      continue;
    }

    if !is_expected_backend_process(pid) {
      write_app_log(
        app,
        "WARN",
        &format!(
          "检测到端口 {} 被未知进程占用，跳过清理 PID={}（{}）",
          BACKEND_PORT, pid, reason
        ),
      );
      continue;
    }

    match kill_process_by_pid(pid) {
      Ok(()) => {
        killed += 1;
        write_app_log(
          app,
          "INFO",
          &format!("已按端口清理后端进程 PID={}（{}）", pid, reason),
        );
      }
      Err(error) => write_app_log(
        app,
        "WARN",
        &format!("按端口清理后端进程失败 PID={}（{}）: {}", pid, reason, error),
      ),
    }
  }

  if killed > 0 {
    for _ in 0..10 {
      if is_backend_port_available() {
        break;
      }
      sleep(Duration::from_millis(200));
    }
  }
}

fn is_expected_backend_process(pid: u32) -> bool {
  #[cfg(target_os = "windows")]
  {
    let output = Command::new("tasklist")
      .args(["/FI", &format!("PID eq {}", pid), "/FO", "CSV", "/NH"])
      .output();

    if let Ok(output) = output {
      let stdout = String::from_utf8_lossy(&output.stdout).to_lowercase();
      return stdout.contains(&BACKEND_EXE_NAME.to_lowercase());
    }

    return false;
  }

  #[cfg(not(target_os = "windows"))]
  {
    let output = Command::new("ps")
      .args(["-p", &pid.to_string(), "-o", "comm="])
      .output();

    if let Ok(output) = output {
      let stdout = String::from_utf8_lossy(&output.stdout).to_lowercase();
      return stdout.contains(&BACKEND_EXE_NAME.to_lowercase());
    }

    false
  }
}

fn cleanup_stale_backend(app: &tauri::AppHandle) {
  let pid_path = match backend_pid_path(app) {
    Ok(path) => path,
    Err(message) => {
      write_app_log(app, "WARN", &message);
      return;
    }
  };

  let pid_text = match read_to_string(&pid_path) {
    Ok(text) => text,
    Err(_) => return,
  };

  let pid = match pid_text.trim().parse::<u32>() {
    Ok(pid) => pid,
    Err(_) => {
      let _ = remove_file(&pid_path);
      write_app_log(app, "WARN", "检测到损坏的后端 PID 文件，已清理");
      return;
    }
  };

  if !is_expected_backend_process(pid) {
    let _ = remove_file(&pid_path);
    write_app_log(
      app,
      "WARN",
      &format!("检测到无效后端 PID 记录，已跳过清理 PID={}", pid),
    );
    return;
  }

  match kill_process_by_pid(pid) {
    Ok(()) => write_app_log(app, "INFO", &format!("已清理残留后端进程 PID={}", pid)),
    Err(message) => write_app_log(app, "WARN", &format!("清理残留后端进程失败 PID={}: {}", pid, message)),
  }

  for _ in 0..10 {
    if is_backend_port_available() {
      break;
    }
    sleep(Duration::from_millis(200));
  }

  let _ = remove_file(pid_path);
}

fn ensure_backend_port_ready(app: &tauri::AppHandle) -> Result<(), String> {
  if is_backend_port_available() {
    return Ok(());
  }

  cleanup_stale_backend(app);

  if is_backend_port_available() {
    return Ok(());
  }

  cleanup_backend_port_occupants(app, "启动前端口兜底清理");

  if is_backend_port_available() {
    return Ok(());
  }

  let message = "应用启动失败，请先关闭占用程序后再打开。".to_string();
  write_app_log(
    app,
    "ERROR",
    &format!("后端端口 {} 已被占用，无法启动应用", BACKEND_PORT),
  );
  Err(message)
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
  #[cfg(target_os = "windows")]
  if !cfg!(debug_assertions) {
    // Hide backend console window in packaged app.
    command.creation_flags(0x08000000);
  }

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

  store_backend_pid(app, child.id());
  write_app_log(app, "INFO", &format!("后端已启动: {}", exe_path.display()));
  Ok(child)
}

fn stop_backend(app: &tauri::AppHandle, reason: &str) {
  let state = app.state::<BackendState>();
  let mut guard = match state.0.lock() {
    Ok(guard) => guard,
    Err(_) => {
      write_app_log(app, "ERROR", "停止后端失败：无法获取进程状态锁");
      clear_backend_pid(app);
      return;
    }
  };

  let child = guard.take();
  drop(guard);

  let Some(mut child) = child else {
    clear_backend_pid(app);
    return;
  };

  let child_pid = child.id();

  let mut wait_exit = false;
  match child.try_wait() {
    Ok(Some(status)) => {
      write_app_log(
        app,
        "INFO",
        &format!("后端已退出，无需重复停止（{}）: {}", reason, status),
      );
    }
    Ok(None) => {
      wait_exit = true;
      if let Err(error) = kill_process_by_pid(child_pid) {
        write_app_log(
          app,
          "WARN",
          &format!(
            "停止后端进程失败 PID={}（{}）: {}",
            child_pid, reason, error
          ),
        );
      }
    }
    Err(error) => {
      wait_exit = true;
      write_app_log(
        app,
        "WARN",
        &format!("检查后端进程状态失败（{}）: {}", reason, error),
      );

      if let Err(kill_error) = kill_process_by_pid(child_pid) {
        write_app_log(
          app,
          "WARN",
          &format!(
            "状态异常时停止后端进程失败 PID={}（{}）: {}",
            child_pid, reason, kill_error
          ),
        );
      }
    }
  }

  if wait_exit {
    match wait_for_child_exit(&mut child, 3000) {
      Ok(true) => {}
      Ok(false) => write_app_log(
        app,
        "WARN",
        &format!("等待后端进程退出超时（{}）", reason),
      ),
      Err(error) => write_app_log(
        app,
        "WARN",
        &format!("等待后端进程退出失败（{}）: {}", reason, error),
      ),
    }
  }

  for _ in 0..10 {
    if is_backend_port_available() {
      break;
    }
    sleep(Duration::from_millis(200));
  }

  if !is_backend_port_available() {
    cleanup_backend_port_occupants(app, reason);
  }

  clear_backend_pid(app);

  if is_backend_port_available() {
    write_app_log(app, "INFO", &format!("已停止后端进程（{}）", reason));
  } else {
    write_app_log(
      app,
      "WARN",
      &format!("后端端口仍被占用（{}），请手动检查进程", reason),
    );
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let app = tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![append_frontend_log])
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
      if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
      }
    }))
    .setup(|app| {
      app.manage(BackendState(Mutex::new(None)));
      write_app_log(app.handle(), "INFO", "主程序启动");
      cleanup_stale_backend(app.handle());

      if let Err(message) = ensure_backend_port_ready(app.handle()) {
        if let Some(win) = app.get_webview_window("main") {
          let _ = win.emit("backend-error", message);
        }
        return Ok(());
      }

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
        stop_backend(&app_handle, "窗口关闭");
      }
    })
    .build(tauri::generate_context!())
    .expect("error while building tauri application");

  app.run(|app_handle, event| {
    match event {
      tauri::RunEvent::Exit => stop_backend(app_handle, "应用退出"),
      tauri::RunEvent::ExitRequested { .. } => stop_backend(app_handle, "应用请求退出"),
      _ => {}
    }
  });
}

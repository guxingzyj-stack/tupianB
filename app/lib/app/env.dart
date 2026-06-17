/// 运行期配置。部署时用 --dart-define 覆盖:
///   flutter run --dart-define=API_BASE_URL=https://xxx.zeabur.app --dart-define=APP_TOKEN=xxx
class Env {
  /// 后端 API 根地址 (不带末尾斜杠)。后端上线后填。
  static const String apiBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');

  /// App 内置 token (架构 §5.2), 随请求带 X-App-Token。
  static const String appToken =
      String.fromEnvironment('APP_TOKEN', defaultValue: '');

  static bool get hasBackend => apiBaseUrl.isNotEmpty;
}

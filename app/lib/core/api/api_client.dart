import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/env.dart';

/// 客户端层异常, message 已是给老人看的人话。
class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

Dio buildDio() {
  final dio = Dio(
    BaseOptions(
      baseUrl: Env.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: {
        if (Env.appToken.isNotEmpty) 'X-App-Token': Env.appToken,
      },
    ),
  );
  dio.interceptors.add(_RetryInterceptor(dio));
  return dio;
}

/// 网络错误自动重试 2 次 (任务 3.4)。
class _RetryInterceptor extends Interceptor {
  final Dio dio;
  final int retries = 2;
  _RetryInterceptor(this.dio);

  static const _retriable = {
    DioExceptionType.connectionTimeout,
    DioExceptionType.receiveTimeout,
    DioExceptionType.sendTimeout,
    DioExceptionType.connectionError,
  };

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final attempt = (err.requestOptions.extra['retry_attempt'] as int?) ?? 0;
    // 慢且昂贵的接口(看图/修图)不自动重试: 超时只是还在等结果, 重试会重复发、重复跑。
    final path = err.requestOptions.path;
    final noAutoRetry =
        path.contains('/api/enhance') || path.contains('/api/analyze');
    if (!noAutoRetry && _retriable.contains(err.type) && attempt < retries) {
      final next = attempt + 1;
      err.requestOptions.extra['retry_attempt'] = next;
      await Future<void>.delayed(Duration(milliseconds: 400 * next));
      try {
        final resp = await dio.fetch<dynamic>(err.requestOptions);
        return handler.resolve(resp);
      } on DioException catch (e) {
        return handler.next(e);
      }
    }
    handler.next(err);
  }
}

/// 把任何错误转成人话 (后端 detail/error 优先)。
String humanError(Object error) {
  if (error is ApiException) return error.message;
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map) {
      final d = data['detail'] ?? data['error'];
      if (d is String && d.isNotEmpty) return d;
    }
  }
  return '网络不太好，稍后再试';
}

final dioProvider = Provider<Dio>((ref) => buildDio());

import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:laozhao/core/api/enhance_api.dart';

/// 真实后端联调测试 (默认跳过)。需要本地后端在跑 + relay 可用。
/// 运行 (在 C:\lz_app):
///   flutter test --dart-define=RUN_LIVE=true --dart-define=LIVE_TOKEN=你的token test/live_backend_test.dart
const _run = bool.fromEnvironment('RUN_LIVE', defaultValue: false);
const _base = String.fromEnvironment('LIVE_BASE', defaultValue: 'http://127.0.0.1:8000');
const _token = String.fromEnvironment('LIVE_TOKEN', defaultValue: '');

void main() {
  test('真实后端: analyze + enhance 全链路', () async {
    final dio = Dio(BaseOptions(
      baseUrl: _base,
      headers: {if (_token.isNotEmpty) 'X-App-Token': _token},
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 45),
    ));
    final api = EnhanceApi(dio);

    final bytes = File('test_images/cheetah.jpg').readAsBytesSync();
    final a = await api.analyze(bytes: bytes, deviceId: 'dev-livetest');
    expect(a.jobId, isNotEmpty);
    expect(a.options.length, 3);
    // ignore: avoid_print
    print('analyze -> job=${a.jobId} scene=${a.scene} '
        'options=${a.options.map((o) => o.name).toList()}');

    final e = await api.enhance(jobId: a.jobId, optionIndex: 0);
    expect(e.resultImageUrl, isNotEmpty);
    // ignore: avoid_print
    print('enhance[0] -> ${e.resultImageUrl} (${e.processingMs}ms)');
  },
      timeout: const Timeout(Duration(seconds: 90)),
      skip: _run ? false : '联调测试: 加 --dart-define=RUN_LIVE=true 并确保后端在跑');
}

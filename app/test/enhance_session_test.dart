import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:laozhao/core/api/api_client.dart';
import 'package:laozhao/core/api/enhance_api.dart';
import 'package:laozhao/core/api/models.dart';
import 'package:laozhao/core/device/device_id.dart';
import 'package:laozhao/features/enhance/state/enhance_session.dart';

class FakeEnhanceApi implements EnhanceApi {
  int analyzeCalls = 0;
  final Map<int, int> enhanceCalls = {};
  bool failAnalyze = false;

  @override
  Future<AnalyzeResult> analyze({
    required Uint8List bytes,
    required String deviceId,
  }) async {
    analyzeCalls++;
    if (failAnalyze) throw ApiException('网络不太好，稍后再试');
    return const AnalyzeResult(
      jobId: 'j_test',
      baseImageUrl: 'http://x/base.jpg',
      scene: '草原',
      subject: '猎豹',
      problems: ['主体偏暗'],
      options: [
        EnhanceOption(name: '豹子更清楚', intent: '主体更清楚'),
        EnhanceOption(name: '暖色草原', intent: '暖色草原'),
        EnhanceOption(name: '天空更蓝', intent: '天空更蓝'),
      ],
    );
  }

  @override
  Future<EnhanceResult> enhance({
    required String jobId,
    required int optionIndex,
  }) async {
    enhanceCalls[optionIndex] = (enhanceCalls[optionIndex] ?? 0) + 1;
    return EnhanceResult(
      resultImageUrl: 'http://x/option_${optionIndex + 1}.jpg',
      optionName: 'opt$optionIndex',
      processingMs: 10,
    );
  }
}

ProviderContainer _container(FakeEnhanceApi api) => ProviderContainer(
      overrides: [
        enhanceApiProvider.overrideWithValue(api),
        deviceIdProvider.overrideWith((ref) async => 'dev-test'),
      ],
    );

void main() {
  test('analyze 成功 -> done + 三选项', () async {
    final api = FakeEnhanceApi();
    final c = _container(api);
    addTearDown(c.dispose);

    final n = c.read(enhanceSessionProvider.notifier);
    n.setOriginal(Uint8List.fromList([1, 2, 3]));
    await n.analyze();

    final s = c.read(enhanceSessionProvider);
    expect(s.status, AnalyzeStatus.done);
    expect(s.analysis!.options.length, 3);
    expect(s.analysis!.options.first.name, '豹子更清楚');
    expect(api.analyzeCalls, 1);
  });

  test('analyze 失败 -> failed + 人话错误', () async {
    final api = FakeEnhanceApi()..failAnalyze = true;
    final c = _container(api);
    addTearDown(c.dispose);

    final n = c.read(enhanceSessionProvider.notifier);
    n.setOriginal(Uint8List.fromList([1]));
    await n.analyze();

    final s = c.read(enhanceSessionProvider);
    expect(s.status, AnalyzeStatus.failed);
    expect(s.error, isNotNull);
  });

  test('selectOption 缓存: 同选项不重复调 enhance', () async {
    final api = FakeEnhanceApi();
    final c = _container(api);
    addTearDown(c.dispose);

    final n = c.read(enhanceSessionProvider.notifier);
    n.setOriginal(Uint8List.fromList([1]));
    await n.analyze();

    await n.selectOption(0);
    await n.selectOption(0); // 第二次命中缓存
    expect(api.enhanceCalls[0], 1);
    expect(c.read(enhanceSessionProvider).optionUrls[0], isNotNull);

    await n.selectOption(1);
    expect(api.enhanceCalls[1], 1);
    expect(c.read(enhanceSessionProvider).selectedIndex, 1);
    expect(c.read(enhanceSessionProvider).selectedUrl, 'http://x/option_2.jpg');
  });

  test('解析后端真实返回结构 (与 analyze.py/enhance.py 契约一致)', () {
    final a = AnalyzeResult.fromJson({
      'job_id': 'j_abc',
      'base_image_url': 'http://h/files/outputs/d/j/base.jpg',
      'analysis': {
        'scene': '草原野生动物',
        'subject': '猎豹',
        'problems': ['主体偏暗', '明暗反差大'],
        'options': [
          {'name': '豹子更清楚', 'intent': '阴影提亮'},
          {'name': '暖色草原', 'intent': '暖调'},
          {'name': '天空更蓝', 'intent': '蓝色加饱和'},
        ],
      },
    });
    expect(a.jobId, 'j_abc');
    expect(a.baseImageUrl, contains('base.jpg'));
    expect(a.options.length, 3);
    expect(a.options[2].name, '天空更蓝');
    expect(a.problems.length, 2);

    final e = EnhanceResult.fromJson({
      'result_image_url': 'http://h/o1.jpg',
      'processing_ms': 1234,
      'option_name': '豹子更清楚',
    });
    expect(e.resultImageUrl, 'http://h/o1.jpg');
    expect(e.processingMs, 1234);
    expect(e.optionName, '豹子更清楚');
  });
}

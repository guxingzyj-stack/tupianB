import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:laozhao/app/router.dart';
import 'package:laozhao/app/theme.dart';
import 'package:laozhao/core/api/media_api.dart';
import 'package:laozhao/core/api/models.dart';
import 'package:laozhao/features/enhance/state/enhance_session.dart';
import 'package:laozhao/features/history/storage/history_db.dart';
import 'package:laozhao/features/history/storage/history_service.dart';

const _cn = 'CN';

final _sampleTemplate = const TemplateItem(
  id: 'midautumn', name: '中秋团圆', videoMotion: 'slow_zoom', imageIntent: '暖色调',
  texts: ['中秋快乐 阖家团圆', '明月寄相思 团圆庆中秋', '千里共婵娟'],
);

List<TemplateCategory> _sampleCats() {
  TemplateItem t(String n) => TemplateItem(id: n, name: n, videoMotion: 'slow_zoom', imageIntent: '', texts: const ['']);
  return [
    TemplateCategory(id: 'festival', name: '节日祝福', templates: [t('新年快乐'), t('中秋团圆'), t('端午安康')]),
    TemplateCategory(id: 'birthday', name: '生日', templates: [t('寿比南山'), t('生日快乐'), t('长命百岁')]),
    TemplateCategory(id: 'animate', name: '让照片动', templates: [t('缓慢推镜'), t('环境微动'), t('人物轻动')]),
    TemplateCategory(id: 'family', name: '全家福', templates: [t('阖家欢乐'), t('三世同堂'), t('岁月静好')]),
  ];
}

Uint8List _thumb(int r, int g, int b) {
  final im = img.Image(width: 320, height: 260);
  img.fill(im, color: img.ColorRgb8(r, g, b));
  img.fillRect(im, x1: 90, y1: 90, x2: 230, y2: 220, color: img.ColorRgb8(60, 50, 40));
  return Uint8List.fromList(img.encodeJpg(im, quality: 80));
}

/// 加载一个 Windows 系统中文字体, 让 golden 截图里中文正常显示。
Future<void> _loadCnFont() async {
  const candidates = [
    r'C:\Windows\Fonts\simhei.ttf',
    r'C:\Windows\Fonts\Deng.ttf',
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\simsun.ttc',
  ];
  for (final path in candidates) {
    final f = File(path);
    if (f.existsSync()) {
      final bytes = f.readAsBytesSync();
      await (FontLoader(_cn)
            ..addFont(Future.value(
                bytes.buffer.asByteData(bytes.offsetInBytes, bytes.lengthInBytes))))
          .load();
      // ignore: avoid_print
      print('golden 用字体: $path');
      return;
    }
  }
}

/// 尽量加载 Material Icons 字体, 让图标不显示成方块 (失败则忽略)。
Future<void> _loadMaterialIcons() async {
  for (final key in const [
    'fonts/MaterialIcons-Regular.otf',
    'packages/flutter/fonts/MaterialIcons-Regular.otf',
  ]) {
    try {
      final data = await rootBundle.load(key);
      await (FontLoader('MaterialIcons')..addFont(Future.value(data))).load();
      return;
    } catch (_) {
      // 试下一个
    }
  }
}

/// 主题已支持 fontFamily 参数, golden 直接传 CN 字体即可 (真机用系统中文字体)。
ThemeData _themedForGolden() => ElderlyTheme.light(fontFamily: _cn);

/// 给结果页/分析中页喂预置会话状态 (不触发真实网络)。
class _PresetSession extends EnhanceSessionNotifier {
  final EnhanceSession _preset;
  _PresetSession(this._preset);
  @override
  EnhanceSession build() => _preset;
  @override
  Future<void> analyze() async {}
  @override
  Future<void> selectOption(int index) async {}
}

AnalyzeResult _demoAnalysis() => const AnalyzeResult(
      jobId: 'j_demo',
      baseImageUrl: null,
      scene: '草原野生动物',
      subject: '猎豹',
      problems: ['主体偏暗'],
      options: [
        EnhanceOption(name: '豹更清楚', intent: '主体提亮'),
        EnhanceOption(name: '暖色草原', intent: '暖调'),
        EnhanceOption(name: '天空更蓝', intent: '蓝色加饱和'),
      ],
    );

void _setView(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

void main() {
  testWidgets('截图: 首页 / 选照片 / 组件预览', (tester) async {
    await _loadCnFont();
    await _loadMaterialIcons();

    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          historyListProvider.overrideWith((ref) async => [
                HistoryEntry(id: '1', createdAt: now, intentName: '动物更清楚', thumb: _thumb(120, 150, 200)),
                HistoryEntry(id: '2', createdAt: now, intentName: '暖色草原', thumb: _thumb(180, 140, 80)),
                HistoryEntry(id: '3', createdAt: now - 86400, intentName: '脸更亮', thumb: _thumb(150, 170, 140)),
              ]),
          templatesProvider.overrideWith((ref) async => _sampleCats()),
        ],
        child: MaterialApp.router(
          theme: _themedForGolden(),
          routerConfig: router,
          debugShowCheckedModeBanner: false,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/01_home.png'));

    router.push('/enhance/select');
    await tester.pumpAndSettle();
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/02_select.png'));

    router.push('/dev/widgets');
    await tester.pump(); // 处理 push, 构建新路由
    await tester.pump(const Duration(milliseconds: 400)); // 推进过场动画到结束
    await tester.pump(const Duration(milliseconds: 200)); // 再走一帧, 离开过场
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/03_widgets.png'));

    router.go('/history');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    // 让 Image.memory 的 JPEG 解码在真实事件循环上跑完, 否则缩略图是空白
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(milliseconds: 300));
    });
    await tester.pumpAndSettle();
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/04_history.png'));

    // 让它动起来 - 选运动方式
    router.push('/video/animate', extra: 'http://x/o.jpg');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/05_animate.png'));

    // 做祝福 - 模板列表
    router.go('/template');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/06_template_list.png'));

    // 做祝福 - 选图选字
    router.push('/template/apply', extra: _sampleTemplate);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/07_template_apply.png'));

    // 子女配置(隐藏页)
    router.go('/');
    router.push('/settings');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/08_settings.png'));
  });

  testWidgets('截图: 分析中', (tester) async {
    await _loadCnFont();
    await _loadMaterialIcons();
    _setView(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhanceSessionProvider.overrideWith(() => _PresetSession(
                EnhanceSession(originalBytes: _thumb(120, 150, 200), status: AnalyzeStatus.analyzing),
              )),
        ],
        child: MaterialApp.router(
            theme: _themedForGolden(), routerConfig: router, debugShowCheckedModeBanner: false),
      ),
    );
    router.go('/enhance/analyzing');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.runAsync(() async => Future<void>.delayed(const Duration(milliseconds: 250)));
    await tester.pump(const Duration(milliseconds: 120));
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/09_analyzing.png'));
  });

  testWidgets('截图: 结果页', (tester) async {
    await _loadCnFont();
    await _loadMaterialIcons();
    _setView(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhanceSessionProvider.overrideWith(() => _PresetSession(
                EnhanceSession(
                  originalBytes: _thumb(150, 120, 90),
                  status: AnalyzeStatus.done,
                  analysis: _demoAnalysis(),
                  optionLoading: true,
                ),
              )),
        ],
        child: MaterialApp.router(
            theme: _themedForGolden(), routerConfig: router, debugShowCheckedModeBanner: false),
      ),
    );
    router.go('/enhance/result/j_demo');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.runAsync(() async => Future<void>.delayed(const Duration(milliseconds: 250)));
    await tester.pump(const Duration(milliseconds: 120));
    await expectLater(
        find.byType(MaterialApp), matchesGoldenFile('goldens/10_result.png'));
  });
}

import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gal/gal.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/api_client.dart';
import '../../../core/widgets/big_button.dart';
import '../../../core/widgets/elderly_app_bar.dart';
import '../../../core/widgets/long_press_compare.dart';
import '../../../core/widgets/option_picker.dart';
import '../../history/storage/history_service.dart';
import '../state/enhance_session.dart';

/// 结果页 (任务 3.5): 大图 + 三选项切换 + 长按对比 + 发家人/保存 + 让它动起来。
class ResultPage extends ConsumerStatefulWidget {
  final String jobId;
  const ResultPage({super.key, required this.jobId});

  @override
  ConsumerState<ResultPage> createState() => _ResultPageState();
}

class _ResultPageState extends ConsumerState<ResultPage> {
  bool _savedToHistory = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final s = ref.read(enhanceSessionProvider);
      if (s.analysis != null && s.selectedUrl == null && !s.optionLoading) {
        ref.read(enhanceSessionProvider.notifier).selectOption(s.selectedIndex);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final s = ref.watch(enhanceSessionProvider);

    // enhance 出错时弹人话提示; 首次出图成功时存历史
    ref.listen(enhanceSessionProvider, (prev, next) {
      if (next.error != null && next.error != prev?.error) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(next.error!, style: const TextStyle(fontSize: 18))),
        );
      }
      final url = next.selectedUrl;
      if (url != null && !_savedToHistory && next.analysis != null) {
        _savedToHistory = true;
        final name = next.analysis!.options[next.selectedIndex].name;
        // 存历史失败不影响主流程
        ref.read(historyServiceProvider).saveFromUrl(url: url, intentName: name);
      }
    });

    if (s.analysis == null || s.originalBytes == null) {
      return Scaffold(
        appBar: const ElderlyAppBar(title: '修好了'),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('照片信息丢了，请重新选一张', style: t.titleMedium),
                const SizedBox(height: 20),
                BigButton(text: '回首页', onPressed: () => context.go('/')),
              ],
            ),
          ),
        ),
      );
    }

    final options = s.analysis!.options;
    return Scaffold(
      appBar: const ElderlyAppBar(title: '修好了'),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _mainImage(s),
              const SizedBox(height: 8),
              Center(
                child: Text('点一下大图,可以看原来的样子',
                    style: t.bodyMedium?.copyWith(color: Colors.black54)),
              ),
              const SizedBox(height: 16),
              Text('想换个样子？', style: t.titleMedium),
              const SizedBox(height: 10),
              OptionPicker(
                options: [
                  for (var i = 0; i < options.length; i++)
                    PickerOption(
                      options[i].name,
                      preview: s.optionUrls[i] != null
                          ? NetworkImage(s.optionUrls[i]!)
                          : null,
                    ),
                ],
                selectedIndex: s.selectedIndex,
                onSelect: (i) =>
                    ref.read(enhanceSessionProvider.notifier).selectOption(i),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: BigButton(
                      text: '发家人',
                      icon: Icons.send,
                      isPrimary: true,
                      onPressed: () => _todo(context, '分享给家人（微信分享开发中）'),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: BigButton(
                      text: '保存',
                      icon: Icons.download,
                      isPrimary: false,
                      onPressed: () => _save(context, s.selectedUrl),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              BigButton(
                text: '让它动起来',
                icon: Icons.movie_creation_outlined,
                isPrimary: false,
                onPressed: () {
                  final url = s.selectedUrl;
                  if (url != null) {
                    context.push('/video/animate', extra: url);
                  } else {
                    _todo(context, '稍等修好图，再让它动起来');
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _mainImage(EnhanceSession s) {
    final url = s.selectedUrl;
    if (url != null) {
      return LongPressCompareView(
        resultImage: NetworkImage(url),
        originalImage: MemoryImage(s.originalBytes!),
      );
    }
    // 结果还没出来: 显示原图 + 加载蒙层
    return Stack(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: AspectRatio(
            aspectRatio: 4 / 3,
            child: Image.memory(s.originalBytes!, fit: BoxFit.cover),
          ),
        ),
        if (s.optionLoading)
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.35),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Center(
                child: CircularProgressIndicator(color: Colors.white),
              ),
            ),
          ),
      ],
    );
  }

  Future<void> _save(BuildContext context, String? url) async {
    if (url == null) {
      _todo(context, '稍等修好图再保存');
      return;
    }
    _todo(context, '正在保存…');
    try {
      final resp = await ref.read(dioProvider).get<List<int>>(
            url,
            options: Options(responseType: ResponseType.bytes),
          );
      await Gal.putImageBytes(Uint8List.fromList(resp.data!));
      if (context.mounted) _todo(context, '已保存到相册');
    } catch (_) {
      if (context.mounted) _todo(context, '保存失败，请重试');
    }
  }

  void _todo(BuildContext context, String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg, style: const TextStyle(fontSize: 18))),
    );
  }
}

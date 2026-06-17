import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/widgets/big_button.dart';
import '../../../core/widgets/elderly_app_bar.dart';
import '../state/enhance_session.dart';

/// 分析中页 (任务 3.4): 立刻显示所选照片, 后台调 analyze,
/// 完成跳结果页, 失败给人话 + 重试。
class AnalyzingPage extends ConsumerStatefulWidget {
  const AnalyzingPage({super.key});

  @override
  ConsumerState<AnalyzingPage> createState() => _AnalyzingPageState();
}

class _AnalyzingPageState extends ConsumerState<AnalyzingPage> {
  bool _navigated = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final s = ref.read(enhanceSessionProvider);
      if (s.originalBytes != null && s.status == AnalyzeStatus.idle) {
        ref.read(enhanceSessionProvider.notifier).analyze();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final s = ref.watch(enhanceSessionProvider);

    // 分析完成 -> 跳结果页 (只跳一次)
    if (s.status == AnalyzeStatus.done && s.analysis != null && !_navigated) {
      _navigated = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.pushReplacement('/enhance/result/${s.analysis!.jobId}');
      });
    }

    return Scaffold(
      appBar: const ElderlyAppBar(title: '正在修图'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              if (s.originalBytes != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: Image.memory(
                    s.originalBytes!,
                    height: 280,
                    width: double.infinity,
                    fit: BoxFit.cover,
                  ),
                ),
              const SizedBox(height: 28),
              Expanded(child: _statusBody(context, t, s)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _statusBody(BuildContext context, TextTheme t, EnhanceSession s) {
    switch (s.status) {
      case AnalyzeStatus.failed:
        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.sentiment_dissatisfied, size: 64),
            const SizedBox(height: 12),
            Text(s.error ?? '网络不太好，稍后再试',
                style: t.titleMedium, textAlign: TextAlign.center),
            const SizedBox(height: 24),
            BigButton(
              text: '重试',
              icon: Icons.refresh,
              onPressed: () => ref.read(enhanceSessionProvider.notifier).analyze(),
            ),
          ],
        );
      case AnalyzeStatus.done:
        return const SizedBox.shrink(); // 即将跳转
      default:
        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(
              width: 48,
              height: 48,
              child: CircularProgressIndicator(strokeWidth: 5),
            ),
            const SizedBox(height: 20),
            Text(
              s.status == AnalyzeStatus.uploading ? '正在上传照片…' : '正在想还有几种修法…',
              style: t.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text('稍等一下就好', style: t.bodyLarge?.copyWith(color: Colors.black54)),
          ],
        );
    }
  }
}

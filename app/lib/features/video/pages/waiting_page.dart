import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/media_api.dart';
import '../../../core/widgets/big_button.dart';
import '../../../core/widgets/elderly_app_bar.dart';
import '../../../core/widgets/waiting_card.dart';

/// "安心等"页 (任务 5.3): 每 5 秒轮询任务, 完成跳视频结果, 失败给人话+再试。
/// 老人可先回首页, 任务在后台继续。
class WaitingPage extends ConsumerStatefulWidget {
  final String jobId;
  const WaitingPage({super.key, required this.jobId});

  @override
  ConsumerState<WaitingPage> createState() => _WaitingPageState();
}

class _WaitingPageState extends ConsumerState<WaitingPage> {
  Timer? _timer;
  String? _error;
  bool _done = false;
  bool _navigated = false;

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _poll());
  }

  Future<void> _poll() async {
    try {
      final st = await ref.read(mediaApiProvider).getJob(widget.jobId);
      if (!mounted) return;
      if (st.isDone && (st.resultUrl?.isNotEmpty ?? false) && !_navigated) {
        _navigated = true;
        _timer?.cancel();
        setState(() => _done = true);
        context.pushReplacement('/video/result', extra: st.resultUrl);
      } else if (st.isFailed) {
        _timer?.cancel();
        setState(() => _error = st.error ?? '没做成，再试一次');
      }
    } catch (_) {
      // 轮询时的临时网络抖动: 忽略, 下次再试
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: const ElderlyAppBar(title: '正在制作'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: _error != null
              ? Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.sentiment_dissatisfied, size: 64),
                    const SizedBox(height: 12),
                    Text(_error!, style: t.titleMedium, textAlign: TextAlign.center),
                    const SizedBox(height: 24),
                    BigButton(text: '再试一次', icon: Icons.refresh, onPressed: () => context.pop()),
                    const SizedBox(height: 12),
                    BigButton(text: '回首页', isPrimary: false, onPressed: () => context.go('/')),
                  ],
                )
              : Column(
                  children: [
                    const Spacer(),
                    WaitingCard(
                      estimatedSeconds: 120,
                      message: '正在让照片动起来',
                      subMessage: '做好了会提醒您，可以先放一边',
                      done: _done,
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: () => context.go('/'),
                      child: Text('先回首页，做好了再看',
                          style: t.bodyLarge?.copyWith(color: Colors.black54)),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

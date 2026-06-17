import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// "安心等"卡片: 大时钟 + 假进度条 + 人话提示 (PRD §8.5)。
/// 假进度从 0 走到 90%, 真正完成 (done=true) 才到 100%。
class WaitingCard extends StatefulWidget {
  final int estimatedSeconds;
  final String message;
  final String? subMessage;
  final bool done;

  const WaitingCard({
    super.key,
    required this.estimatedSeconds,
    required this.message,
    this.subMessage,
    this.done = false,
  });

  @override
  State<WaitingCard> createState() => _WaitingCardState();
}

class _WaitingCardState extends State<WaitingCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
      vsync: this,
      duration: Duration(seconds: widget.estimatedSeconds.clamp(2, 600)),
    )..forward();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final primary = Theme.of(context).colorScheme.primary;
    final minutes = (widget.estimatedSeconds / 60).ceil();

    return Container(
      decoration: BoxDecoration(
        color: ElderlyTheme.surface,
        borderRadius: BorderRadius.circular(ElderlyTheme.radiusLg),
        boxShadow: ElderlyTheme.shadowSoft,
      ),
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                color: primary.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(
                widget.done ? Icons.check_circle_rounded : Icons.access_time_rounded,
                size: 52,
                color: primary,
              ),
            ),
            const SizedBox(height: 20),
            Text(widget.message, style: t.titleLarge, textAlign: TextAlign.center),
            const SizedBox(height: 20),
            AnimatedBuilder(
              animation: _c,
              builder: (_, _) {
                final v = widget.done ? 1.0 : _c.value * 0.9;
                return ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: LinearProgressIndicator(
                    value: v,
                    minHeight: 16,
                    backgroundColor: ElderlyTheme.line,
                    valueColor: AlwaysStoppedAnimation(primary),
                  ),
                );
              },
            ),
            const SizedBox(height: 16),
            Text(
              widget.done ? '做好了' : '大约 $minutes 分钟',
              style: t.titleMedium,
            ),
            if (widget.subMessage != null) ...[
              const SizedBox(height: 8),
              Text(
                widget.subMessage!,
                style: t.bodyMedium,
                textAlign: TextAlign.center,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

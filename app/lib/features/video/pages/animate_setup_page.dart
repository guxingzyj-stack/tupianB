import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/api/media_api.dart';
import '../../../core/device/device_id.dart';
import '../../../core/widgets/big_button.dart';
import '../../../core/widgets/elderly_app_bar.dart';

/// 让它动起来 - 选运动方式 (任务 5.3)。
class AnimateSetupPage extends ConsumerStatefulWidget {
  final String imageUrl;
  const AnimateSetupPage({super.key, required this.imageUrl});

  @override
  ConsumerState<AnimateSetupPage> createState() => _AnimateSetupPageState();
}

class _AnimateSetupPageState extends ConsumerState<AnimateSetupPage> {
  String _motion = 'slow_zoom';
  bool _busy = false;

  static const _options = [
    ('slow_zoom', '缓慢推镜', '镜头慢慢推近，最稳当'),
    ('env_breeze', '环境微动', '草木、水面轻轻动，人不动'),
    ('subtle_human', '人物轻动', '头发衣角轻动，不动表情'),
  ];

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      final deviceId = await ref.read(deviceIdProvider.future);
      final jobId = await ref.read(mediaApiProvider).createVideo(
            deviceId: deviceId,
            imageUrl: widget.imageUrl,
            motion: _motion,
          );
      if (mounted) context.push('/video/waiting', extra: jobId);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e', style: const TextStyle(fontSize: 18))),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: const ElderlyAppBar(title: '让它动起来'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: AspectRatio(
                  aspectRatio: 4 / 3,
                  child: Image.network(
                    widget.imageUrl,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => Container(
                      color: Colors.black12,
                      child: const Icon(Icons.image, size: 48, color: Colors.black38),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text('想怎么动？', style: t.titleMedium),
              const SizedBox(height: 10),
              for (final o in _options) ...[
                _MotionTile(
                  label: o.$2,
                  desc: o.$3,
                  selected: _motion == o.$1,
                  onTap: () => setState(() => _motion = o.$1),
                ),
                const SizedBox(height: 10),
              ],
              const Spacer(),
              BigButton(
                text: _busy ? '正在提交…' : '开始制作',
                icon: Icons.movie_creation_outlined,
                onPressed: _busy ? null : _start,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MotionTile extends StatelessWidget {
  final String label;
  final String desc;
  final bool selected;
  final VoidCallback onTap;
  const _MotionTile({required this.label, required this.desc, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: selected ? primary : Colors.black26, width: selected ? 3 : 1.4),
        ),
        child: Row(
          children: [
            Icon(selected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                color: selected ? primary : Colors.black38, size: 28),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: ElderlyTheme.ink)),
                  const SizedBox(height: 2),
                  Text(desc, style: const TextStyle(fontSize: 15, color: ElderlyTheme.subtle)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

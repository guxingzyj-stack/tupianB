import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';

/// 首页 (PRD §3.1): 品牌 + 问候 + 两个大渐变卡片 + 语音入口。
/// 子女配置入口隐藏在问候语长按 (PRD §3.8 / §11)。
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 品牌 + 历史入口
              Row(
                children: [
                  const Icon(Icons.auto_awesome, color: ElderlyTheme.primary, size: 24),
                  const SizedBox(width: 7),
                  Text('老照',
                      style: t.titleLarge?.copyWith(
                          color: ElderlyTheme.primary, fontWeight: FontWeight.w800)),
                  const Spacer(),
                  _CircleIconButton(
                    icon: Icons.photo_library_outlined,
                    tooltip: '我修过的照片',
                    onTap: () => context.push('/history'),
                  ),
                ],
              ),
              const SizedBox(height: 22),
              GestureDetector(
                onLongPress: () => context.push('/settings'), // 隐藏: 子女配置
                child: Text('您想做什么？', style: t.headlineLarge),
              ),
              const SizedBox(height: 20),
              Expanded(
                child: _HeroTile(
                  title: '修照片',
                  subtitle: '模糊、发暗、老照片，都能修清楚',
                  icon: Icons.auto_fix_high_rounded,
                  gradient: ElderlyTheme.warmGrad,
                  onTap: () => context.push('/enhance/select'),
                ),
              ),
              const SizedBox(height: 18),
              Expanded(
                child: _HeroTile(
                  title: '做祝福',
                  subtitle: '做成会动的祝福小视频，发给家人',
                  icon: Icons.card_giftcard_rounded,
                  gradient: ElderlyTheme.tealGrad,
                  onTap: () => context.push('/template'),
                ),
              ),
              const SizedBox(height: 18),
              Center(
                child: _VoicePill(
                  onTap: () => ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('语音帮忙马上就来', style: TextStyle(fontSize: 18))),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CircleIconButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;
  const _CircleIconButton({required this.icon, required this.tooltip, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Container(
        decoration: BoxDecoration(
          color: ElderlyTheme.surface,
          shape: BoxShape.circle,
          boxShadow: ElderlyTheme.shadowCard,
        ),
        child: Material(
          color: Colors.transparent,
          shape: const CircleBorder(),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(13),
              child: Icon(icon, size: 28, color: ElderlyTheme.ink),
            ),
          ),
        ),
      ),
    );
  }
}

class _HeroTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Gradient gradient;
  final VoidCallback onTap;
  const _HeroTile({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.gradient,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: gradient,
        borderRadius: BorderRadius.circular(ElderlyTheme.radiusLg),
        boxShadow: ElderlyTheme.shadowSoft,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(ElderlyTheme.radiusLg),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Stack(
            children: [
              // 装饰大图标 (增加层次)
              Positioned(
                right: -16,
                bottom: -22,
                child: Icon(icon, size: 150, color: Colors.white.withValues(alpha: 0.13)),
              ),
              Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      width: 60,
                      height: 60,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.22),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(icon, size: 34, color: Colors.white),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(
                              fontSize: 33, fontWeight: FontWeight.w800, color: Colors.white),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          subtitle,
                          style: TextStyle(
                              fontSize: 16.5,
                              height: 1.3,
                              color: Colors.white.withValues(alpha: 0.92)),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _VoicePill extends StatelessWidget {
  final VoidCallback onTap;
  const _VoicePill({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: ElderlyTheme.surface,
      borderRadius: BorderRadius.circular(28),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(28),
            boxShadow: ElderlyTheme.shadowCard,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.mic_none_rounded, size: 22, color: ElderlyTheme.subtle),
              const SizedBox(width: 8),
              Text('不会点？说一声也行',
                  style: TextStyle(fontSize: 16, color: ElderlyTheme.subtle)),
            ],
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../app/theme.dart';

/// 全局统一大按钮。高度≥62、字24粗、按下有触觉反馈 (PRD §4.2)。
class BigButton extends StatelessWidget {
  final String text;
  final IconData? icon;
  final VoidCallback? onPressed;
  final bool isPrimary;
  final Color? color; // 覆盖主色, 如危险红

  const BigButton({
    super.key,
    required this.text,
    this.icon,
    this.onPressed,
    this.isPrimary = true,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    void handle() {
      HapticFeedback.lightImpact();
      onPressed?.call();
    }

    final child = Row(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[
          Icon(icon, size: 28),
          const SizedBox(width: 10),
        ],
        Flexible(
          child: Text(text,
              textAlign: TextAlign.center, overflow: TextOverflow.ellipsis),
        ),
      ],
    );

    if (isPrimary) {
      return ElevatedButton(
        onPressed: onPressed == null ? null : handle,
        style: ElevatedButton.styleFrom(
          backgroundColor: color ?? scheme.primary,
          foregroundColor: Colors.white,
        ),
        child: child,
      );
    }
    return OutlinedButton(
      onPressed: onPressed == null ? null : handle,
      style: OutlinedButton.styleFrom(
        foregroundColor: color ?? ElderlyTheme.ink,
        side: BorderSide(color: color ?? ElderlyTheme.ink, width: 1.6),
      ),
      child: child,
    );
  }
}

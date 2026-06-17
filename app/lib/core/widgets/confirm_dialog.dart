import 'dart:async';

import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// 二次确认弹窗: 大字大按钮, 危险操作主按钮红色,
/// 带超时自动取消兜底 (PRD §4.4 弹窗须有自动关闭兜底)。
class ConfirmDialog {
  static Future<bool> show(
    BuildContext context, {
    required String title,
    String? message,
    String confirmText = '确定',
    String cancelText = '取消',
    bool danger = false,
    Duration autoCancel = const Duration(seconds: 10),
  }) async {
    Timer? timer;
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        timer = Timer(autoCancel, () {
          if (Navigator.of(ctx).canPop()) Navigator.of(ctx).pop(false);
        });
        final t = Theme.of(ctx).textTheme;
        return AlertDialog(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          title: Text(title, style: t.titleLarge),
          content: message != null
              ? Text(message, style: t.bodyLarge)
              : null,
          actionsPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          actions: [
            OutlinedButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              style: OutlinedButton.styleFrom(minimumSize: const Size(120, 56)),
              child: Text(cancelText),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(120, 56),
                backgroundColor: danger ? ElderlyTheme.danger : null,
              ),
              child: Text(confirmText),
            ),
          ],
        );
      },
    );
    timer?.cancel();
    return result ?? false;
  }
}

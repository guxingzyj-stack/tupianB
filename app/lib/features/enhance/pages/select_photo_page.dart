import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../core/widgets/big_button.dart';
import '../../../core/widgets/elderly_app_bar.dart';
import '../providers/photo_picker_provider.dart';
import '../state/enhance_session.dart';

/// 选照片 (PRD §3.1 / 任务 3.3)。选完把字节写入会话, 跳分析中页。
class SelectPhotoPage extends ConsumerWidget {
  const SelectPhotoPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: const ElderlyAppBar(title: '想修哪张？'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              const SizedBox(height: 8),
              Text('选一张照片，我来帮您修', style: t.bodyLarge),
              const SizedBox(height: 28),
              BigButton(
                text: '从相册选',
                icon: Icons.photo,
                isPrimary: true,
                onPressed: () => _pick(context, ref, ImageSource.gallery),
              ),
              const SizedBox(height: 16),
              BigButton(
                text: '现场拍照',
                icon: Icons.camera_alt,
                isPrimary: false,
                onPressed: () => _pickCamera(context, ref),
              ),
              const SizedBox(height: 16),
              BigButton(
                text: '拍纸质老照片',
                icon: Icons.collections,
                isPrimary: false,
                onPressed: () => _shootOldPhoto(context),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _pick(
      BuildContext context, WidgetRef ref, ImageSource source) async {
    try {
      final picked = await ref.read(photoPickerProvider).pick(source);
      if (picked == null) return; // 用户取消
      ref.read(enhanceSessionProvider.notifier).setOriginal(picked.bytes);
      if (context.mounted) context.push('/enhance/analyzing');
    } catch (_) {
      if (context.mounted) {
        _permissionHint(
            context, source == ImageSource.camera ? '相机打不开，去设置里看看权限' : '需要相册权限才能选照片');
      }
    }
  }

  Future<void> _pickCamera(BuildContext context, WidgetRef ref) async {
    final status = await Permission.camera.request();
    if (status.isPermanentlyDenied || status.isDenied) {
      if (context.mounted) _permissionHint(context, '需要相机权限才能拍照');
      return;
    }
    if (context.mounted) await _pick(context, ref, ImageSource.camera);
  }

  void _shootOldPhoto(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text('功能开发中'),
        content: const Text(
          '拍纸质老照片马上就好，先用"从相册选"或"现场拍照"吧。',
          style: TextStyle(fontSize: 18, height: 1.4),
        ),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            style: ElevatedButton.styleFrom(minimumSize: const Size(110, 52)),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  void _permissionHint(BuildContext context, String msg) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text('需要权限'),
        content: Text(msg, style: const TextStyle(fontSize: 18, height: 1.4)),
        actions: [
          OutlinedButton(
            onPressed: () => Navigator.pop(context),
            style: OutlinedButton.styleFrom(minimumSize: const Size(100, 52)),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              openAppSettings();
            },
            style: ElevatedButton.styleFrom(minimumSize: const Size(100, 52)),
            child: const Text('去设置'),
          ),
        ],
      ),
    );
  }
}

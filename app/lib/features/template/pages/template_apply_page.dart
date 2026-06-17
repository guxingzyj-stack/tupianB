import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/api/media_api.dart';
import '../../../core/device/device_id.dart';
import '../../../core/widgets/big_button.dart';
import '../../../core/widgets/elderly_app_bar.dart';
import '../../enhance/providers/photo_picker_provider.dart';

/// 做祝福 - 选图 + 选祝福语 + 开始 (任务 5.4)。
class TemplateApplyPage extends ConsumerStatefulWidget {
  final TemplateItem template;
  const TemplateApplyPage({super.key, required this.template});

  @override
  ConsumerState<TemplateApplyPage> createState() => _TemplateApplyPageState();
}

class _TemplateApplyPageState extends ConsumerState<TemplateApplyPage> {
  Uint8List? _bytes;
  int _textIndex = 0;
  bool _busy = false;

  String _label(String s) => s.trim().isEmpty ? '（不加字）' : s;

  Future<void> _pick() async {
    try {
      final picked = await ref.read(photoPickerProvider).pick(ImageSource.gallery);
      if (picked != null) setState(() => _bytes = picked.bytes);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('需要相册权限才能选照片', style: TextStyle(fontSize: 18))),
        );
      }
    }
  }

  Future<void> _start() async {
    if (_bytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('先选一张照片吧', style: TextStyle(fontSize: 18))),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final deviceId = await ref.read(deviceIdProvider.future);
      final api = ref.read(mediaApiProvider);
      final imageUrl = await api.upload(bytes: _bytes!, deviceId: deviceId);
      final jobId = await api.applyTemplate(
        deviceId: deviceId,
        templateId: widget.template.id,
        imageUrl: imageUrl,
        textIndex: _textIndex,
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
    final texts = widget.template.texts;
    return Scaffold(
      appBar: ElderlyAppBar(title: widget.template.name),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('选一张照片', style: t.titleMedium),
            const SizedBox(height: 10),
            GestureDetector(
              onTap: _pick,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: AspectRatio(
                  aspectRatio: 4 / 3,
                  child: _bytes != null
                      ? Image.memory(_bytes!, fit: BoxFit.cover)
                      : Container(
                          color: Colors.black12,
                          child: const Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.add_photo_alternate, size: 48, color: Colors.black45),
                                SizedBox(height: 8),
                                Text('点这里选照片', style: TextStyle(fontSize: 17, color: Colors.black54)),
                              ],
                            ),
                          ),
                        ),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text('选一句祝福', style: t.titleMedium),
            const SizedBox(height: 10),
            for (int i = 0; i < texts.length; i++) ...[
              _TextOption(
                text: _label(texts[i]),
                selected: _textIndex == i,
                onTap: () => setState(() => _textIndex = i),
              ),
              const SizedBox(height: 10),
            ],
            const SizedBox(height: 10),
            BigButton(
              text: _busy ? '正在提交…' : '开始制作',
              icon: Icons.auto_awesome,
              onPressed: _busy ? null : _start,
            ),
          ],
        ),
      ),
    );
  }
}

class _TextOption extends StatelessWidget {
  final String text;
  final bool selected;
  final VoidCallback onTap;
  const _TextOption({required this.text, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: selected ? primary : Colors.black26, width: selected ? 3 : 1.4),
        ),
        child: Text(text,
            style: TextStyle(fontSize: 19, fontWeight: selected ? FontWeight.w700 : FontWeight.w500)),
      ),
    );
  }
}

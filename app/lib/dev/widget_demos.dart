import 'package:flutter/material.dart';

import '../app/theme.dart';
import '../core/widgets/big_button.dart';
import '../core/widgets/confirm_dialog.dart';
import '../core/widgets/elderly_app_bar.dart';
import '../core/widgets/option_picker.dart';
import '../core/widgets/waiting_card.dart';

/// 通用组件 demo (任务 3.2 验收用)。debug 下访问 /dev/widgets。
class WidgetDemosPage extends StatefulWidget {
  const WidgetDemosPage({super.key});

  @override
  State<WidgetDemosPage> createState() => _WidgetDemosPageState();
}

class _WidgetDemosPageState extends State<WidgetDemosPage> {
  int _sel = 0;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    Widget section(String s) => Padding(
          padding: const EdgeInsets.only(top: 24, bottom: 8),
          child: Text(s, style: t.titleMedium),
        );

    return Scaffold(
      appBar: const ElderlyAppBar(title: '组件预览'),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          section('大按钮 BigButton'),
          BigButton(text: '发家人', icon: Icons.send, onPressed: () {}),
          const SizedBox(height: 12),
          BigButton(
              text: '保存', icon: Icons.download, isPrimary: false, onPressed: () {}),
          const SizedBox(height: 12),
          BigButton(
            text: '删除',
            icon: Icons.delete_outline,
            isPrimary: false,
            color: ElderlyTheme.danger,
            onPressed: () {},
          ),
          section('三选项 OptionPicker'),
          OptionPicker(
            options: const [
              PickerOption('动物更清楚'),
              PickerOption('暖色草原'),
              PickerOption('天空更蓝'),
            ],
            selectedIndex: _sel,
            onSelect: (i) => setState(() => _sel = i),
          ),
          section('安心等 WaitingCard'),
          const WaitingCard(
            estimatedSeconds: 120,
            message: '正在让照片动起来',
            subMessage: '做好了会提醒您，可以先放一边',
          ),
          section('二次确认 ConfirmDialog'),
          BigButton(
            text: '弹一个确认框',
            isPrimary: false,
            onPressed: () async {
              final ok = await ConfirmDialog.show(
                context,
                title: '要删除吗？',
                message: '删了就找不回来了',
                confirmText: '删除',
                danger: true,
              );
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(ok ? '已删除' : '取消了',
                        style: const TextStyle(fontSize: 18)),
                  ),
                );
              }
            },
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

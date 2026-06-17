import 'package:flutter/material.dart';

import '../../core/widgets/elderly_app_bar.dart';

/// 子女配置页 (隐藏, 经首页长按标题进入)。
/// 完整配置项见 PRD §11 (API Key / 日预算 / 偏好 / 视频开关等), 后续实现。
class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: const ElderlyAppBar(title: '子女配置'),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('这里是给子女用的配置（老人看不到）。', style: t.bodyLarge),
            const SizedBox(height: 16),
            Text('待实现 (PRD §11)：API Key、日预算上限、默认样式、'
                '微信分享目标、视频开关、老照片动起来开关。',
                style: t.bodyMedium?.copyWith(color: Colors.black54)),
            const Spacer(),
            Center(
              child: GestureDetector(
                onLongPress: () => ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('高级配置入口（开发中）',
                        style: TextStyle(fontSize: 18)),
                  ),
                ),
                child: Text('版本 v0.1.0',
                    style: t.bodyMedium?.copyWith(color: Colors.black38)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

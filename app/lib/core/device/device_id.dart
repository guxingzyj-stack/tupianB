import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 设备标识 (架构 §5.1): 首次启动生成, 存本地, 所有 API 调用都带。
Future<String> loadOrCreateDeviceId() async {
  final sp = await SharedPreferences.getInstance();
  var id = sp.getString('device_id');
  if (id == null || id.isEmpty) {
    final r = Random.secure();
    final hex = List.generate(
      16,
      (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
    id = 'dev-$hex';
    await sp.setString('device_id', id);
  }
  return id;
}

final deviceIdProvider = FutureProvider<String>((ref) => loadOrCreateDeviceId());

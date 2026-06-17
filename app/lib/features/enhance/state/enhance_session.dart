import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/enhance_api.dart';
import '../../../core/api/models.dart';
import '../../../core/device/device_id.dart';

enum AnalyzeStatus { idle, uploading, analyzing, done, failed }

const Object _undef = Object();

/// 一次修图会话的全部状态: 原图 + 分析结果 + 选项结果缓存。
class EnhanceSession {
  final Uint8List? originalBytes;
  final AnalyzeStatus status;
  final AnalyzeResult? analysis;
  final String? error;
  final int selectedIndex;
  final Map<int, String> optionUrls; // 选项 index -> 结果图 URL (缓存)
  final bool optionLoading;

  const EnhanceSession({
    this.originalBytes,
    this.status = AnalyzeStatus.idle,
    this.analysis,
    this.error,
    this.selectedIndex = 0,
    this.optionUrls = const {},
    this.optionLoading = false,
  });

  EnhanceSession copyWith({
    Object? originalBytes = _undef,
    AnalyzeStatus? status,
    Object? analysis = _undef,
    Object? error = _undef,
    int? selectedIndex,
    Map<int, String>? optionUrls,
    bool? optionLoading,
  }) {
    return EnhanceSession(
      originalBytes:
          originalBytes == _undef ? this.originalBytes : originalBytes as Uint8List?,
      status: status ?? this.status,
      analysis: analysis == _undef ? this.analysis : analysis as AnalyzeResult?,
      error: error == _undef ? this.error : error as String?,
      selectedIndex: selectedIndex ?? this.selectedIndex,
      optionUrls: optionUrls ?? this.optionUrls,
      optionLoading: optionLoading ?? this.optionLoading,
    );
  }

  String? get selectedUrl => optionUrls[selectedIndex];
}

class EnhanceSessionNotifier extends Notifier<EnhanceSession> {
  @override
  EnhanceSession build() => const EnhanceSession();

  /// 选完照片后调用, 重置会话。
  void setOriginal(Uint8List bytes) {
    state = EnhanceSession(originalBytes: bytes);
  }

  /// 调 /api/analyze。永不抛错, 失败进 failed 状态。
  Future<void> analyze() async {
    final bytes = state.originalBytes;
    if (bytes == null) return;
    state = state.copyWith(status: AnalyzeStatus.uploading, error: null);
    try {
      final deviceId = await ref.read(deviceIdProvider.future);
      state = state.copyWith(status: AnalyzeStatus.analyzing);
      final result =
          await ref.read(enhanceApiProvider).analyze(bytes: bytes, deviceId: deviceId);
      state = state.copyWith(status: AnalyzeStatus.done, analysis: result, error: null);
    } catch (e) {
      state = state.copyWith(status: AnalyzeStatus.failed, error: humanError(e));
    }
  }

  /// 切换选项: 命中缓存直接用, 否则调 /api/enhance。
  Future<void> selectOption(int index) async {
    final analysis = state.analysis;
    if (analysis == null) return;
    state = state.copyWith(selectedIndex: index, error: null);
    if (state.optionUrls.containsKey(index)) return; // 缓存命中, 不重复调
    state = state.copyWith(optionLoading: true);
    try {
      final r = await ref
          .read(enhanceApiProvider)
          .enhance(jobId: analysis.jobId, optionIndex: index);
      final updated = Map<int, String>.from(state.optionUrls)
        ..[index] = r.resultImageUrl;
      state = state.copyWith(optionUrls: updated, optionLoading: false);
    } catch (e) {
      state = state.copyWith(optionLoading: false, error: humanError(e));
    }
  }
}

final enhanceSessionProvider =
    NotifierProvider<EnhanceSessionNotifier, EnhanceSession>(
        EnhanceSessionNotifier.new);

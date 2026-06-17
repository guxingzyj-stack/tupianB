import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'models.dart';

/// 修图相关 API: analyze (看图三选项) + enhance (按选项出图)。
class EnhanceApi {
  final Dio _dio;
  EnhanceApi(this._dio);

  Future<AnalyzeResult> analyze({
    required Uint8List bytes,
    required String deviceId,
  }) async {
    try {
      final resp = await _dio.post<dynamic>(
        '/api/analyze',
        data: {'device_id': deviceId, 'image': base64Encode(bytes)},
        // 看图要上传整图 + 等 Claude + 处理, 放宽超时 (全局默认 30s 偏紧)
        options: Options(
          sendTimeout: const Duration(seconds: 60),
          receiveTimeout: const Duration(seconds: 90),
        ),
      );
      return AnalyzeResult.fromJson((resp.data as Map).cast<String, dynamic>());
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }

  Future<EnhanceResult> enhance({
    required String jobId,
    required int optionIndex,
  }) async {
    try {
      final resp = await _dio.post<dynamic>(
        '/api/enhance',
        data: {'job_id': jobId, 'option_index': optionIndex},
        // 生成式修复 (gpt-image-2) 约 40-65s, 远超全局默认 30s; 放宽到 150s 等出图
        options: Options(receiveTimeout: const Duration(seconds: 150)),
      );
      return EnhanceResult.fromJson((resp.data as Map).cast<String, dynamic>());
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }
}

final enhanceApiProvider =
    Provider<EnhanceApi>((ref) => EnhanceApi(ref.watch(dioProvider)));

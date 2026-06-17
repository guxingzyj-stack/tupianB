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
      );
      return EnhanceResult.fromJson((resp.data as Map).cast<String, dynamic>());
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }
}

final enhanceApiProvider =
    Provider<EnhanceApi>((ref) => EnhanceApi(ref.watch(dioProvider)));

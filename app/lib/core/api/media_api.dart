import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class JobStatus {
  final String status; // pending / running / success / failed
  final int progress;
  final String? resultUrl;
  final String? error;

  const JobStatus({required this.status, required this.progress, this.resultUrl, this.error});

  bool get isDone => status == 'success';
  bool get isFailed => status == 'failed';

  factory JobStatus.fromJson(Map<String, dynamic> j) => JobStatus(
        status: (j['status'] ?? 'pending').toString(),
        progress: (j['progress'] is int) ? j['progress'] as int : int.tryParse('${j['progress']}') ?? 0,
        resultUrl: j['result_url'] as String?,
        error: j['error'] as String?,
      );
}

class TemplateItem {
  final String id;
  final String name;
  final String videoMotion;
  final String imageIntent;
  final List<String> texts;

  const TemplateItem({
    required this.id,
    required this.name,
    required this.videoMotion,
    required this.imageIntent,
    required this.texts,
  });

  factory TemplateItem.fromJson(Map<String, dynamic> j) => TemplateItem(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        videoMotion: (j['video_motion'] ?? 'slow_zoom').toString(),
        imageIntent: (j['image_intent'] ?? '').toString(),
        texts: (j['texts'] as List?)?.map((e) => e.toString()).toList() ?? const [],
      );
}

class TemplateCategory {
  final String id;
  final String name;
  final List<TemplateItem> templates;
  const TemplateCategory({required this.id, required this.name, required this.templates});

  factory TemplateCategory.fromJson(Map<String, dynamic> j) => TemplateCategory(
        id: (j['id'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        templates: (j['templates'] as List?)
                ?.map((e) => TemplateItem.fromJson((e as Map).cast<String, dynamic>()))
                .toList() ??
            const [],
      );
}

class MediaApi {
  final Dio _dio;
  MediaApi(this._dio);

  Future<String> upload({required Uint8List bytes, required String deviceId}) async {
    try {
      final r = await _dio.post<dynamic>('/api/upload',
          data: {'device_id': deviceId, 'image': base64Encode(bytes)});
      return (r.data['image_url'] ?? '').toString();
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }

  Future<String> createVideo({
    required String deviceId,
    required String imageUrl,
    required String motion,
  }) async {
    try {
      final r = await _dio.post<dynamic>('/api/video',
          data: {'device_id': deviceId, 'image_url': imageUrl, 'motion': motion});
      return (r.data['job_id'] ?? '').toString();
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }

  Future<JobStatus> getJob(String jobId) async {
    try {
      final r = await _dio.get<dynamic>('/api/jobs/$jobId');
      return JobStatus.fromJson((r.data as Map).cast<String, dynamic>());
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }

  Future<List<TemplateCategory>> listTemplates() async {
    try {
      final r = await _dio.get<dynamic>('/api/templates');
      final cats = (r.data['categories'] as List?) ?? const [];
      return cats.map((e) => TemplateCategory.fromJson((e as Map).cast<String, dynamic>())).toList();
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }

  Future<String> applyTemplate({
    required String deviceId,
    required String templateId,
    required String imageUrl,
    required int textIndex,
  }) async {
    try {
      final r = await _dio.post<dynamic>('/api/template/apply', data: {
        'device_id': deviceId,
        'template_id': templateId,
        'image_url': imageUrl,
        'text_index': textIndex,
      });
      return (r.data['job_id'] ?? '').toString();
    } on DioException catch (e) {
      throw ApiException(humanError(e));
    }
  }
}

final mediaApiProvider = Provider<MediaApi>((ref) => MediaApi(ref.watch(dioProvider)));

final templatesProvider = FutureProvider<List<TemplateCategory>>(
  (ref) => ref.watch(mediaApiProvider).listTemplates(),
);

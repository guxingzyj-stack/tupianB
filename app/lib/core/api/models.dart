// 后端返回的数据模型 (对应架构 §3.6)。

class EnhanceOption {
  final String name;
  final String intent;
  const EnhanceOption({required this.name, required this.intent});

  factory EnhanceOption.fromJson(Map<String, dynamic> j) => EnhanceOption(
        name: (j['name'] ?? '').toString(),
        intent: (j['intent'] ?? '').toString(),
      );
}

class AnalyzeResult {
  final String jobId;
  final String? baseImageUrl;
  final String scene;
  final String subject;
  final List<String> problems;
  final List<EnhanceOption> options;

  const AnalyzeResult({
    required this.jobId,
    required this.baseImageUrl,
    required this.scene,
    required this.subject,
    required this.problems,
    required this.options,
  });

  factory AnalyzeResult.fromJson(Map<String, dynamic> j) {
    final a = (j['analysis'] as Map?)?.cast<String, dynamic>() ?? const {};
    return AnalyzeResult(
      jobId: (j['job_id'] ?? '').toString(),
      baseImageUrl: j['base_image_url'] as String?,
      scene: (a['scene'] ?? '').toString(),
      subject: (a['subject'] ?? '').toString(),
      problems: (a['problems'] as List?)?.map((e) => e.toString()).toList() ?? const [],
      options: (a['options'] as List?)
              ?.map((e) => EnhanceOption.fromJson((e as Map).cast<String, dynamic>()))
              .toList() ??
          const [],
    );
  }
}

class EnhanceResult {
  final String resultImageUrl;
  final String optionName;
  final int processingMs;

  const EnhanceResult({
    required this.resultImageUrl,
    required this.optionName,
    required this.processingMs,
  });

  factory EnhanceResult.fromJson(Map<String, dynamic> j) => EnhanceResult(
        resultImageUrl: (j['result_image_url'] ?? '').toString(),
        optionName: (j['option_name'] ?? '').toString(),
        processingMs: (j['processing_ms'] ?? 0) is int
            ? j['processing_ms'] as int
            : int.tryParse('${j['processing_ms']}') ?? 0,
      );
}

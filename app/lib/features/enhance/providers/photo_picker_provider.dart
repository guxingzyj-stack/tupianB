import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

/// 选到的图: 直接拿字节 (跨平台, web/桌面/真机都行, 不碰 dart:io)。
class PickedImage {
  final Uint8List bytes;
  final String name;
  const PickedImage(this.bytes, this.name);
}

final photoPickerProvider = Provider<PhotoPicker>((ref) => PhotoPicker());

class PhotoPicker {
  final ImagePicker _picker = ImagePicker();

  /// 上传前已限制长边 ≤2400 (任务 3.4)。取消返回 null。
  Future<PickedImage?> pick(ImageSource source) async {
    final x = await _picker.pickImage(
      source: source,
      maxWidth: 2400,
      maxHeight: 2400,
      imageQuality: 92,
    );
    if (x == null) return null;
    return PickedImage(await x.readAsBytes(), x.name);
  }
}

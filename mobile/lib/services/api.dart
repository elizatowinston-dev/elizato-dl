import 'dart:convert'; import 'dart:io'; import 'package:http/http.dart' as http;
class Api {
  Api(this.base, this.deviceId); final String base,deviceId;
  Map<String,String> get headers=>{'X-Device-ID':deviceId};
  Future<Map<String,dynamic>> preview(String url, File cookies) async => _multipart('/v1/playlists/preview',{'url':url},cookies);
  Future<Map<String,dynamic>> start(String url,String format,bool lyrics,File cookies) => _multipart('/v1/jobs',{'url':url,'format':format,'lyrics':'$lyrics'},cookies);
  Future<Map<String,dynamic>> status(String id) async { final r=await http.get(Uri.parse('$base/v1/jobs/$id'),headers:headers); return _json(r); }
  Future<Map<String,dynamic>> _multipart(String route,Map<String,String> fields,File file) async {final r=http.MultipartRequest('POST',Uri.parse('$base$route'))..headers.addAll(headers)..fields.addAll(fields)..files.add(await http.MultipartFile.fromPath('cookies','${file.path}')); final s=await r.send(); return _json(await http.Response.fromStream(s));}
  Map<String,dynamic> _json(http.Response r){if(r.statusCode>=300)throw Exception('Server error ${r.statusCode}'); return jsonDecode(r.body) as Map<String,dynamic>;}
}

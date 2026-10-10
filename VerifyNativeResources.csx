using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Security.Cryptography;
using UndertaleModLib.Util;
EnsureDataLoaded();
var root=Path.Combine(Environment.CurrentDirectory,"work","beastieball");
var inputs=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"staging","font-resources","resource-build-inputs.json"))).RootElement;
var patch=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"staging","embedded","string-patch.json"))).RootElement;
foreach(var entry in patch.GetProperty("records").EnumerateArray()){
 using(var sha=SHA256.Create()){
  var actual=BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(Data.Strings[entry.GetProperty("index").GetInt32()].Content))).Replace("-","").ToLowerInvariant();
  if(actual!=entry.GetProperty("source_sha256").GetString())throw new Exception("Embedded English was altered");
 }
}
foreach(var entry in inputs.GetProperty("fonts").EnumerateArray()){
 var font=Data.Fonts.ByName(entry.GetProperty("font").GetString());
 var expected=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"staging","font-resources",font.Name.Content+".glyphs.json"))).RootElement;
 if(font.Glyphs.Count!=expected.GetArrayLength())throw new Exception("Serialized glyph count mismatch");
 foreach(var g in expected.EnumerateArray()){
  var actual=font.Glyphs.Single(x=>x.Character==g.GetProperty("character").GetInt32());
  if(actual.SourceX!=g.GetProperty("x").GetInt32()||actual.SourceY!=g.GetProperty("y").GetInt32()||actual.SourceWidth!=g.GetProperty("w").GetInt32()||actual.SourceHeight!=g.GetProperty("h").GetInt32()||actual.Shift!=g.GetProperty("shift").GetInt32()||actual.Offset!=g.GetProperty("offset").GetInt32())throw new Exception("Serialized glyph geometry mismatch");
 }
 var image=font.Texture.TexturePage.TextureData.Image;
 var texture=font.Texture.TexturePage;
 if(texture.TextureWidth!=2048||texture.TextureHeight!=2048||texture.TextureInfo==null||!texture.TextureInfo.TexturePages.Any(p=>p.Resource==texture))throw new Exception("Texture dimensions or group registration missing");
 if(image.Width!=2048||image.Height!=2048)throw new Exception("Serialized texture size mismatch");
 var sourceImage=GMImage.FromPng(File.ReadAllBytes(Path.Combine(root,"staging","font-resources",font.Name.Content+".png")));
 if(!image.ConvertToRawBgra().GetRawImageData().SequenceEqual(sourceImage.ConvertToRawBgra().GetRawImageData()))throw new Exception("Serialized texture pixel payload mismatch");
}
var report=new{fonts_verified=5,embedded_english_strings_preserved=patch.GetProperty("records").GetArrayLength(),serialized_resource_roundtrip=true,native_rendering_verified=false,installable_candidate_ready=false};
File.WriteAllText(Path.Combine(root,"review","serialized-resource-verification.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine(JsonSerializer.Serialize(report));

// Workspace-only GameMaker resource candidate builder. Not a runtime shaper.
// Run against the supported original through UndertaleModCli; save only to staging.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using UndertaleModLib.Util;
EnsureDataLoaded();
var root=Path.Combine(Environment.CurrentDirectory,"work","beastieball");
var assets=Path.Combine(root,"staging","font-resources");
var inputs=JsonDocument.Parse(File.ReadAllText(Path.Combine(assets,"resource-build-inputs.json"))).RootElement;
var patch=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"staging","embedded","string-patch.json"))).RootElement;
string Digest(byte[] b){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(b)).Replace("-","").ToLowerInvariant();}
if(Data.Strings.Count!=inputs.GetProperty("original_string_count").GetInt32()||Data.Fonts.Count!=inputs.GetProperty("original_font_count").GetInt32())throw new Exception("Unsupported original resources");
if(patch.GetProperty("original_sha256").GetString()!=inputs.GetProperty("original_data_sha256").GetString())throw new Exception("Mismatched resource inputs");
// Validate every original binding and asset before making any in-memory changes.
foreach(var entry in patch.GetProperty("records").EnumerateArray()){
 int index=entry.GetProperty("index").GetInt32();
 if(index<0||index>=Data.Strings.Count||Digest(Encoding.UTF8.GetBytes(Data.Strings[index].Content))!=entry.GetProperty("source_sha256").GetString())throw new Exception("Unsupported original source string "+index);
}
foreach(var entry in inputs.GetProperty("fonts").EnumerateArray()){
 string name=entry.GetProperty("font").GetString();var font=Data.Fonts.ByName(name);
 if(font==null||font.Glyphs.Count!=entry.GetProperty("original_glyph_count").GetInt32())throw new Exception("Unsupported original font "+name);
 var png=File.ReadAllBytes(Path.Combine(assets,name+".png"));if(Digest(png)!=entry.GetProperty("atlas_sha256").GetString())throw new Exception("Changed bitmap "+name);
 var glyphs=JsonDocument.Parse(File.ReadAllText(Path.Combine(assets,name+".glyphs.json"))).RootElement;
 var chars=glyphs.EnumerateArray().Select(g=>g.GetProperty("character").GetInt32()).ToArray();
 if(chars.Length!=chars.Distinct().Count()||chars.Any(c=>c<0||c>65535)||font.Glyphs.Any(g=>!chars.Contains(g.Character)))throw new Exception("Missing original glyph or invalid mapping "+name);
}
foreach(var entry in inputs.GetProperty("fonts").EnumerateArray()){
 string name=entry.GetProperty("font").GetString();var font=Data.Fonts.ByName(name);
 var texture=new UndertaleEmbeddedTexture();texture.Name=Data.Strings.MakeString("BeastieballArabic_"+name);
 texture.TextureWidth=2048;texture.TextureHeight=2048;texture.Scaled=font.Texture.TexturePage.Scaled;
 var group=font.Texture.TexturePage.TextureInfo;
 if(group==null)throw new Exception("Original font has no texture group "+name);
 texture.IndexInGroup=group.TexturePages.Count;texture.TextureInfo=group;
 texture.TextureData.Image=GMImage.FromPng(File.ReadAllBytes(Path.Combine(assets,name+".png")));Data.EmbeddedTextures.Add(texture);
 group.TexturePages.Add(new UndertaleModLib.UndertaleResourceById<UndertaleEmbeddedTexture,UndertaleModLib.UndertaleChunkTXTR>{Resource=texture});
 var page=new UndertaleTexturePageItem();page.Name=Data.Strings.MakeString("BeastieballArabicPage_"+name);
 page.SourceWidth=2048;page.SourceHeight=2048;page.TargetWidth=2048;page.TargetHeight=2048;page.BoundingWidth=2048;page.BoundingHeight=2048;page.TexturePage=texture;
 Data.TexturePageItems.Add(page);font.Texture=page;font.DisplayName=Data.Strings.MakeString(entry.GetProperty("role").GetString()=="normal"?"Saudi":"Academia Friendly");
 var glyphs=JsonDocument.Parse(File.ReadAllText(Path.Combine(assets,name+".glyphs.json"))).RootElement;
 font.Glyphs.Clear();
 foreach(var g in glyphs.EnumerateArray())font.Glyphs.Add(new UndertaleFont.Glyph{Character=checked((ushort)g.GetProperty("character").GetInt32()),SourceX=checked((ushort)g.GetProperty("x").GetInt32()),SourceY=checked((ushort)g.GetProperty("y").GetInt32()),SourceWidth=checked((ushort)g.GetProperty("w").GetInt32()),SourceHeight=checked((ushort)g.GetProperty("h").GetInt32()),Shift=checked((short)g.GetProperty("shift").GetInt32()),Offset=checked((short)g.GetProperty("offset").GetInt32())});
 font.RangeEnd=Math.Max(font.RangeEnd,font.Glyphs[font.Glyphs.Count-1].Character);
 Console.WriteLine(name+": "+font.Glyphs.Count+" glyphs; original characters retained");
}
// Embedded English remains intact. The conditional native text router supplies
// Arabic only when Russian is selected; permanent STRG translation would break
// the user's requested immediate return to English.
Console.WriteLine("Font resource candidate prepared; embedded English retained for language switching.");


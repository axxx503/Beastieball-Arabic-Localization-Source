using System;
using System.IO;
using System.Linq;
using System.Text.Json;
EnsureDataLoaded();
var root=Path.Combine(Environment.CurrentDirectory,"work","beastieball","reverse");
Directory.CreateDirectory(root);
var opts=new JsonSerializerOptions{WriteIndented=true};
var fonts=Data.Fonts.Select(f=>new{
 name=f.Name.Content,display=f.DisplayName.Content,size=f.EmSize,bold=f.Bold,italic=f.Italic,
 glyphCount=f.Glyphs.Count,
 texture=f.Texture==null?null:new{f.Texture.SourceX,f.Texture.SourceY,f.Texture.SourceWidth,f.Texture.SourceHeight},
 glyphs=f.Glyphs.Select(g=>new{g.Character,g.SourceX,g.SourceY,g.SourceWidth,g.SourceHeight,g.Shift,g.Offset})
});
File.WriteAllText(Path.Combine(root,"font-inventory.json"),JsonSerializer.Serialize(fonts,opts));
File.WriteAllText(Path.Combine(root,"scripts.txt"),String.Join("\n",Data.Scripts.Select(s=>s.Name.Content)));
File.WriteAllText(Path.Combine(root,"strings.json"),JsonSerializer.Serialize(Data.Strings.Select(s=>s.Content),opts));
File.WriteAllText(Path.Combine(root,"general-info.txt"),Data.GeneralInfo.ToString());
Console.WriteLine("Read-only inventory written: "+root);

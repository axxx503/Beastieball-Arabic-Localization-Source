using System;
using System.IO;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Collections.Generic;
// Workspace-only bitmap cache renderer. Uses glyph indices from unchanged TTF.
public static class RenderOriginalGlyphs {
 [StructLayout(LayoutKind.Sequential)] struct Point { public int x,y; }
 [StructLayout(LayoutKind.Sequential)] struct Metrics { public uint width,height; public Point origin; public short advanceX,advanceY; }
 [StructLayout(LayoutKind.Sequential)] struct Fixed { public ushort fraction; public short value; }
 [StructLayout(LayoutKind.Sequential)] struct Matrix { public Fixed a,b,c,d; }
 [DllImport("gdi32.dll",CharSet=CharSet.Unicode)] static extern int AddFontResourceEx(string p,uint flags,IntPtr zero);
 [DllImport("gdi32.dll",CharSet=CharSet.Unicode)] static extern bool RemoveFontResourceEx(string p,uint flags,IntPtr zero);
 [DllImport("gdi32.dll")] static extern IntPtr CreateCompatibleDC(IntPtr dc);
 [DllImport("gdi32.dll")] static extern bool DeleteDC(IntPtr dc);
 [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr o);
 [DllImport("gdi32.dll")] static extern IntPtr SelectObject(IntPtr dc,IntPtr o);
 [DllImport("gdi32.dll",CharSet=CharSet.Unicode)] static extern IntPtr CreateFont(int height,int width,int escape,int orientation,int weight,uint italic,uint underline,uint strike,uint charset,uint precision,uint clip,uint quality,uint pitch,string family);
 [DllImport("gdi32.dll",CharSet=CharSet.Unicode)] static extern uint GetGlyphOutline(IntPtr dc,uint glyph,uint format,out Metrics metrics,uint size,byte[] pixels,ref Matrix matrix);
 [DllImport("gdi32.dll")] static extern uint GetFontData(IntPtr dc,uint table,uint offset,byte[] data,uint size);
 public static int Main(string[] args) {
  if(args.Length!=6) throw new ArgumentException("font family glyphs.tsv output-prefix pixel-size original-head.bin");
  string font=Path.GetFullPath(args[0]),prefix=Path.GetFullPath(args[3]);
  if(AddFontResourceEx(font,16,IntPtr.Zero)==0)throw new Exception("Private original font load failed");
  IntPtr dc=IntPtr.Zero,face=IntPtr.Zero,old=IntPtr.Zero;
  try {
   dc=CreateCompatibleDC(IntPtr.Zero);face=CreateFont(-int.Parse(args[4]),0,0,0,400,0,0,0,1,0,0,4,0,args[1]);
   if(dc==IntPtr.Zero||face==IntPtr.Zero)throw new Exception("GDI setup failed");
   old=SelectObject(dc,face);var matrix=new Matrix{a=new Fixed{value=1},d=new Fixed{value=1}};
   byte[] expected=File.ReadAllBytes(args[5]);uint headSize=GetFontData(dc,0x64616568,0,null,0);
   if(headSize!=expected.Length)throw new Exception("Original font identity mismatch: head length");
   byte[] actual=new byte[headSize];if(GetFontData(dc,0x64616568,0,actual,headSize)!=headSize)throw new Exception("Cannot verify original selected font");
   for(int i=0;i<actual.Length;i++)if(actual[i]!=expected[i])throw new Exception("Original font identity mismatch: head bytes");
   using(var atlas=new Bitmap(2048,2048,PixelFormat.Format32bppArgb)) {
    var lines=new List<string>{"character\tglyph_id\tx\ty\twidth\theight\tadvance\torigin_x\torigin_y"};
    int x=2,y=2,rowHeight=0;
    foreach(string line in File.ReadAllLines(args[2])) {
     if(String.IsNullOrWhiteSpace(line))continue;var cols=line.Split('\t');uint cp=uint.Parse(cols[0]),gid=uint.Parse(cols[1]);Metrics m;
     uint size=GetGlyphOutline(dc,gid,0x80|6,out m,0,null,ref matrix);
     if(size==0xffffffff)throw new Exception("Glyph rasterization failed "+gid);
     int w=(int)m.width,h=(int)m.height;
     if(x+w+2>atlas.Width){x=2;y+=rowHeight+3;rowHeight=0;}
     if(y+h+2>atlas.Height)throw new Exception("Atlas overflow");
     if(size>0){byte[] pixels=new byte[size];if(GetGlyphOutline(dc,gid,0x80|6,out m,size,pixels,ref matrix)==0xffffffff)throw new Exception("Glyph bitmap read failed");
      int stride=(w+3)&~3;for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++){int a=Math.Min(255,pixels[yy*stride+xx]*255/64);atlas.SetPixel(x+xx,y+yy,Color.FromArgb(a,255,255,255));}}
     lines.Add(String.Join("\t",new object[]{cp,gid,x,y,w,h,m.advanceX,m.origin.x,m.origin.y}));
     x+=Math.Max(w,1)+3;rowHeight=Math.Max(rowHeight,h);
    }
    atlas.Save(prefix+".png",ImageFormat.Png);File.WriteAllLines(prefix+".tsv",lines);
   }
   Console.WriteLine("Original font identity verified; rendered glyph bitmap cache: "+prefix);return 0;
  } finally {if(old!=IntPtr.Zero)SelectObject(dc,old);if(face!=IntPtr.Zero)DeleteObject(face);if(dc!=IntPtr.Zero)DeleteDC(dc);RemoveFontResourceEx(font,16,IntPtr.Zero);}
 }
}

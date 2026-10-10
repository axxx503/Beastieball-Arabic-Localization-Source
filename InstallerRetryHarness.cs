using System;
using System.IO;
using System.Reflection;
public static class InstallerRetryHarness {
 public static int Main(string[] args){
  typeof(Installer).GetMethod("Prepare",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
  try{Installer.Install(args[0]);Installer.Remove(args[0]);Installer.Install(args[0]);Installer.Remove(args[0]);Console.WriteLine("Same-session install/remove/install/remove passed.");return 0;}
  finally{
   string taskTemp=(string)typeof(Installer).GetField("payload",BindingFlags.Static|BindingFlags.NonPublic).GetValue(null);
   string absolute=Path.GetFullPath(taskTemp),tempRoot=Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\')+"\\";
   if(!absolute.StartsWith(tempRoot,StringComparison.OrdinalIgnoreCase)||!Path.GetFileName(absolute).StartsWith("BeastieballArabic-"))throw new Exception("Unsafe temporary cleanup path");
   Directory.Delete(absolute,true);
  }
 }
}

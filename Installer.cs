using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

public class PatchEntry { public string Path; public string Patch; public string Original; public string Target; }
public class PatchManifest { public string Version; public string English; public List<PatchEntry> Files; }
public static class Installer {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static string payload;
 static PatchManifest manifest;
 static readonly string[] Allowed={"beastieball.exe","data.win","loc/Русский.csv","ftText.yy","ftBold.yy","ftUI.yy","ftSport.yy","ftEditor.yy"};
 static string Hash(string path){using(var stream=File.OpenRead(path))using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
 static string Join(string root,string relative){
  if(Path.IsPathRooted(relative)||relative.Split('/','\\').Any(p=>p==".."||p==""))throw new Exception("Invalid package path");
  string full=Path.GetFullPath(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));
  if(!full.StartsWith(Path.GetFullPath(root).TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase))throw new Exception("Path escapes installation directory");
  return full;
 }
 static void NeedHash(string path,string hash){if(!File.Exists(path)||Hash(path)!=hash)throw new Exception("الملف غير مطابق للنسخة المدعومة: "+path);}
 static void Prepare(){
  payload=Path.Combine(Path.GetTempPath(),"BeastieballArabic-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(payload);
  using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))using(var zip=new ZipArchive(stream,ZipArchiveMode.Read))
   foreach(var entry in zip.Entries){if(entry.FullName.EndsWith("/"))continue;string dst=Join(payload,entry.FullName);Directory.CreateDirectory(Path.GetDirectoryName(dst));entry.ExtractToFile(dst);}
  manifest=Json.Deserialize<PatchManifest>(File.ReadAllText(Path.Combine(payload,"manifest.json"),Encoding.UTF8));
  if(manifest.Files.Count!=Allowed.Length||manifest.Files.Select(f=>f.Path).Distinct().Count()!=Allowed.Length||manifest.Files.Any(f=>!Allowed.Contains(f.Path)))throw new Exception("Invalid package manifest");
 }
 static string Backup(string game){return Path.Combine(game,".beastieball-arabic-backup");}
 static void CheckEnglish(string game){NeedHash(Join(game,"loc/English.csv"),manifest.English);}
 static void CheckGameClosed(){if(Process.GetProcessesByName("beastieball").Length>0)throw new Exception("أغلق Beastieball قبل التثبيت أو الإزالة.");}
 static void RunPatch(string source,string delta,string destination){
  var psi=new ProcessStartInfo(Path.Combine(payload,"xdelta3.exe"),"-f -d -s \""+source+"\" \""+delta+"\" \""+destination+"\"");
  psi.UseShellExecute=false;psi.CreateNoWindow=true;psi.WindowStyle=ProcessWindowStyle.Hidden;psi.RedirectStandardError=true;
  using(var proc=Process.Start(psi)){string error=proc.StandardError.ReadToEnd();proc.WaitForExit();if(proc.ExitCode!=0)throw new Exception("تعذر تطبيق الباتش: "+error);}
 }
 static void Upgrade(string game,string backup){
  string savedPath=Path.Combine(backup,"manifest.json"),statePath=Path.Combine(backup,"installed.json");
  byte[] savedBytes=File.ReadAllBytes(savedPath),stateBytes=File.ReadAllBytes(statePath);
  var old=Json.Deserialize<PatchManifest>(Encoding.UTF8.GetString(savedBytes).TrimStart('\uFEFF'));
  if(old.Files.Count!=Allowed.Length||old.Files.Select(f=>f.Path).Distinct().Count()!=Allowed.Length||old.Files.Any(f=>!Allowed.Contains(f.Path)))throw new Exception("بيانات النسخة السابقة غير صالحة؛ لم تُعدّل اللعبة.");
  foreach(var f in manifest.Files){var previous=old.Files.Single(o=>o.Path==f.Path);if(previous.Original!=f.Original)throw new Exception("أصل النسخة السابقة مختلف؛ أوقفت التحديث.");NeedHash(Join(backup,f.Path),f.Original);NeedHash(Join(game,f.Path),previous.Target);}
  string stage=Path.Combine(payload,"upgrade"),rollback=Path.Combine(payload,"previous");
  foreach(var f in manifest.Files){
   string dst=Join(stage,f.Path),prior=Join(rollback,f.Path);Directory.CreateDirectory(Path.GetDirectoryName(dst));Directory.CreateDirectory(Path.GetDirectoryName(prior));
   RunPatch(Join(backup,f.Path),Join(payload,f.Patch),dst);NeedHash(dst,f.Target);File.Copy(Join(game,f.Path),prior,true);NeedHash(prior,old.Files.Single(o=>o.Path==f.Path).Target);
  }
  var changed=new List<PatchEntry>();
  try{
   foreach(var f in manifest.Files){changed.Add(f);File.Copy(Join(stage,f.Path),Join(game,f.Path),true);NeedHash(Join(game,f.Path),f.Target);}
   CheckEnglish(game);File.WriteAllText(savedPath,Json.Serialize(manifest),Encoding.UTF8);File.WriteAllText(statePath,Json.Serialize(new{Version=manifest.Version}),Encoding.UTF8);
  }catch{
   foreach(var f in changed){File.Copy(Join(rollback,f.Path),Join(game,f.Path),true);NeedHash(Join(game,f.Path),old.Files.Single(o=>o.Path==f.Path).Target);}
   File.WriteAllBytes(savedPath,savedBytes);File.WriteAllBytes(statePath,stateBytes);throw;
  }
 }
 public static void Install(string game){
  game=Path.GetFullPath(game);CheckGameClosed();CheckEnglish(game);
  string backup=Backup(game);
  if(Directory.Exists(backup)){
   if(!File.Exists(Path.Combine(backup,"installed.json")))throw new Exception("توجد نسخة احتياطية غير مكتملة. لم تُعدّل الملفات؛ افحصها أولًا.");
   var installed=Json.Deserialize<PatchManifest>(File.ReadAllText(Path.Combine(backup,"manifest.json"),Encoding.UTF8));
   if(installed.Version!=manifest.Version){Upgrade(game,backup);return;}
   foreach(var f in manifest.Files)NeedHash(Join(game,f.Path),f.Target);return;
  }
  foreach(var f in manifest.Files)NeedHash(Join(game,f.Path),f.Original);
  string stage=Path.Combine(payload,"prepared");Directory.CreateDirectory(stage);
  // Decode and verify the entire candidate before touching any game file.
  foreach(var f in manifest.Files){string dst=Join(stage,f.Path);Directory.CreateDirectory(Path.GetDirectoryName(dst));RunPatch(Join(game,f.Path),Join(payload,f.Patch),dst);NeedHash(dst,f.Target);}
  Directory.CreateDirectory(backup);
  foreach(var f in manifest.Files){string dst=Join(backup,f.Path);Directory.CreateDirectory(Path.GetDirectoryName(dst));File.Copy(Join(game,f.Path),dst);NeedHash(dst,f.Original);}
  File.WriteAllText(Path.Combine(backup,"manifest.json"),Json.Serialize(manifest),Encoding.UTF8);
  var changed=new List<PatchEntry>();
  try{
   foreach(var f in manifest.Files){changed.Add(f);File.Copy(Join(stage,f.Path),Join(game,f.Path),true);NeedHash(Join(game,f.Path),f.Target);}
   CheckEnglish(game);File.WriteAllText(Path.Combine(backup,"installed.json"),Json.Serialize(new{Version=manifest.Version}),Encoding.UTF8);
  }catch{
   foreach(var f in changed){File.Copy(Join(backup,f.Path),Join(game,f.Path),true);NeedHash(Join(game,f.Path),f.Original);}
   throw;
  }
 }
 public static void Remove(string game){
  game=Path.GetFullPath(game);CheckGameClosed();CheckEnglish(game);string backup=Backup(game);
  if(!File.Exists(Path.Combine(backup,"manifest.json")))throw new Exception("لا توجد نسخة احتياطية لهذا التعريب.");
  var saved=Json.Deserialize<PatchManifest>(File.ReadAllText(Path.Combine(backup,"manifest.json"),Encoding.UTF8));
  if(saved.Version!=manifest.Version)throw new Exception("استخدم مثبت نسخة التعريب التي ثبتها للإزالة.");
  foreach(var f in manifest.Files){NeedHash(Join(backup,f.Path),f.Original);string hash=Hash(Join(game,f.Path));if(hash!=f.Target&&hash!=f.Original)throw new Exception("ملف اللعبة تغير بعد التثبيت؛ أوقفت الاسترجاع لحمايته: "+f.Path);}
  foreach(var f in manifest.Files){File.Copy(Join(backup,f.Path),Join(game,f.Path),true);NeedHash(Join(game,f.Path),f.Original);}
  CheckEnglish(game);
  // Delete only known backup files after successful byte-exact restoration.
  foreach(var f in manifest.Files)File.Delete(Join(backup,f.Path));
  File.Delete(Path.Combine(backup,"installed.json"));File.Delete(Path.Combine(backup,"manifest.json"));
  string loc=Path.Combine(backup,"loc");if(Directory.Exists(loc)&&!Directory.EnumerateFileSystemEntries(loc).Any())Directory.Delete(loc);
  if(!Directory.EnumerateFileSystemEntries(backup).Any())Directory.Delete(backup);
 }
 [STAThread] public static int Main(string[] args){
  try{
   Prepare();
   if(args.Length==2){if(args[0]=="--install")Install(args[1]);else if(args[0]=="--remove")Remove(args[1]);else throw new Exception("Unknown operation");return 0;}
   Application.EnableVisualStyles();
   var form=new Form{Text="Beastieball — التعريب العربي (نسخة تجربة)",Width=620,Height=245,StartPosition=FormStartPosition.CenterScreen,FormBorderStyle=FormBorderStyle.FixedDialog,MaximizeBox=false,RightToLeft=RightToLeft.Yes,RightToLeftLayout=true};
   var info=new Label{Left=20,Top=15,Width=560,Height=55,Text="أغلق اللعبة قبل التثبيت. اختر Русский من إعدادات اللغة، ثم أغلق اللعبة وأعد تشغيلها لتطبيق العربية بالكامل. عند العودة إلى English أعد التشغيل أيضًا."};
   var path=new TextBox{Left=20,Top=80,Width=465,Text=@"H:\SteamLibrary\steamapps\common\Beastieball",RightToLeft=RightToLeft.No};
   var browse=new Button{Left=495,Top=78,Width=85,Text="المجلد"};browse.Click+=(s,e)=>{using(var dialog=new FolderBrowserDialog()){dialog.SelectedPath=path.Text;if(dialog.ShowDialog()==DialogResult.OK)path.Text=dialog.SelectedPath;}};
   var install=new Button{Left=200,Top=125,Width=180,Height=40,Text="تثبيت التعريب"};var remove=new Button{Left=20,Top=125,Width=165,Height=40,Text="إزالة واسترجاع الأصل"};
   Action<bool> act=add=>{install.Enabled=remove.Enabled=browse.Enabled=false;try{if(add)Install(path.Text);else Remove(path.Text);MessageBox.Show(add?"تم التثبيت. اختر Русский داخل اللعبة لتفعيل العربية.":"تمت الإزالة واستعادة الأصول.","Beastieball");}catch(Exception ex){MessageBox.Show(ex.Message,"لم تكتمل العملية",MessageBoxButtons.OK,MessageBoxIcon.Error);}finally{install.Enabled=remove.Enabled=browse.Enabled=true;}};
   install.Click+=(s,e)=>act(true);remove.Click+=(s,e)=>act(false);form.Controls.AddRange(new Control[]{info,path,browse,install,remove});Application.Run(form);return 0;
  }catch(Exception ex){File.WriteAllText(Path.Combine(Path.GetTempPath(),"BeastieballArabic-Installer-error.txt"),ex.ToString());if(args.Length==0)MessageBox.Show(ex.Message);return 1;}
  finally{if(payload!=null&&Directory.Exists(payload))Directory.Delete(payload,true);}
 }
}

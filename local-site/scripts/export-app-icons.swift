import AppKit
import Foundation

struct App: Decodable { let id: String; let name: String; let path: String }
let args=CommandLine.arguments
guard args.count == 3 else { fatalError("usage: export-app-icons apps.json output-folder") }
let apps=try JSONDecoder().decode([App].self,from:Data(contentsOf:URL(fileURLWithPath:args[1])))
let output=URL(fileURLWithPath:args[2],isDirectory:true)
try FileManager.default.createDirectory(at:output,withIntermediateDirectories:true)
var manifest=[String:[String:String]]()
for app in apps {
    guard app.id.range(of:"^[A-Za-z0-9._-]+$",options:.regularExpression) != nil else { continue }
    // Read app-bundle metadata/artwork only; do not launch or control any app.
    let icon=NSWorkspace.shared.icon(forFile:app.path)
    guard let bitmap=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:64,pixelsHigh:64,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0),let context=NSGraphicsContext(bitmapImageRep:bitmap) else { continue }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current=context
    icon.draw(in:NSRect(x:0,y:0,width:64,height:64),from:.zero,operation:.copy,fraction:1)
    NSGraphicsContext.restoreGraphicsState()
    guard let png=bitmap.representation(using:.png,properties:[:]) else { continue }
    try png.write(to:output.appendingPathComponent(app.id+".png"),options:.atomic)
    manifest[app.id]=["name":app.name,"icon":"/app-icons/"+app.id+".png"]
}
let encoded=try JSONSerialization.data(withJSONObject:manifest,options:[.prettyPrinted,.sortedKeys])
try encoded.write(to:output.appendingPathComponent("installed-manifest.json"),options:.atomic)
print("Exported \(manifest.count) local application icons")

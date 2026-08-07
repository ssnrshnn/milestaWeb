// Renders the 1200x630 Open Graph / Twitter card image for milesta.app.
// Mirrors the site hero: cream gradient, terracotta winding trail, the three
// coloured waypoint dots, the app icon and the tagline.
//
//   swift make_og_image.swift <icon.png> <out.png>

import Foundation
import CoreGraphics
import CoreText
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 3 else {
    FileHandle.standardError.write("usage: make_og_image.swift <icon.png> <out.png>\n".data(using: .utf8)!)
    exit(1)
}
let iconPath = args[1]
let outPath = args[2]

let W = 1200.0, H = 630.0

func rgb(_ r: Int, _ g: Int, _ b: Int, _ a: CGFloat = 1) -> CGColor {
    CGColor(red: CGFloat(r) / 255, green: CGFloat(g) / 255, blue: CGFloat(b) / 255, alpha: a)
}

let bgTop     = rgb(0xfa, 0xf7, 0xf2)
let bgBottom  = rgb(0xf3, 0xed, 0xe4)
let ink       = rgb(0x2e, 0x2a, 0x25)
let inkSoft   = rgb(0x8a, 0x81, 0x77)
let accent    = rgb(0xc0, 0x85, 0x5a)
let card      = rgb(0xff, 0xfd, 0xf9)
let dotRed    = rgb(0xd8, 0x55, 0x5c)
let dotBlue   = rgb(0x5b, 0x8d, 0xbe)
let dotGreen  = rgb(0x6a, 0xa8, 0x77)

let space = CGColorSpaceCreateDeviceRGB()
guard let ctx = CGContext(data: nil, width: Int(W), height: Int(H), bitsPerComponent: 8,
                          bytesPerRow: 0, space: space,
                          bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
    fatalError("could not create context")
}

// Flip to a top-left origin so the layout numbers read like CSS.
ctx.translateBy(x: 0, y: H)
ctx.scaleBy(x: 1, y: -1)

// --- background ------------------------------------------------------------
let gradient = CGGradient(colorsSpace: space, colors: [bgTop, bgBottom] as CFArray,
                          locations: [0, 1])!
ctx.drawLinearGradient(gradient, start: .zero, end: CGPoint(x: 0, y: H), options: [])

// --- the winding trail, running the full width behind the text -------------
// Same shape as the hero SVG (viewBox 320x150), scaled and pushed low.
func trailPoint(_ x: Double, _ y: Double) -> CGPoint {
    // viewBox 320x150 -> the lower band, clear of the text block above
    CGPoint(x: 40 + x * (1120.0 / 320.0), y: 425 + y * (190.0 / 150.0))
}

let trail = CGMutablePath()
trail.move(to: trailPoint(20, 130))
trail.addCurve(to: trailPoint(160, 40), control1: trailPoint(90, 130), control2: trailPoint(90, 40))
trail.addCurve(to: trailPoint(300, 110), control1: trailPoint(230, 40), control2: trailPoint(230, 110))

ctx.saveGState()
ctx.setStrokeColor(accent.copy(alpha: 0.85)!)
ctx.setLineWidth(10)
ctx.setLineCap(.round)
ctx.addPath(trail)
ctx.strokePath()
ctx.restoreGState()

func waypoint(_ p: CGPoint, _ color: CGColor) {
    let r = 17.0
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -4), blur: 12,
                  color: rgb(0x50, 0x32, 0x1e, 0.28))
    ctx.setFillColor(color)
    ctx.fillEllipse(in: CGRect(x: p.x - r, y: p.y - r, width: r * 2, height: r * 2))
    ctx.restoreGState()
    ctx.setStrokeColor(card)
    ctx.setLineWidth(6)
    ctx.strokeEllipse(in: CGRect(x: p.x - r, y: p.y - r, width: r * 2, height: r * 2))
}

waypoint(trailPoint(20, 130), dotRed)
waypoint(trailPoint(160, 40), dotBlue)
waypoint(trailPoint(300, 110), dotGreen)

// --- app icon --------------------------------------------------------------
if let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: iconPath) as CFURL, nil),
   let icon = CGImageSourceCreateImageAtIndex(src, 0, nil) {
    let side = 136.0
    let rect = CGRect(x: 72, y: 60, width: side, height: side)
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -14), blur: 34,
                  color: rgb(0x50, 0x32, 0x1e, 0.30))
    ctx.setFillColor(card)
    ctx.addPath(CGPath(roundedRect: rect, cornerWidth: 31, cornerHeight: 31, transform: nil))
    ctx.fillPath()
    ctx.restoreGState()

    ctx.saveGState()
    ctx.addPath(CGPath(roundedRect: rect, cornerWidth: 31, cornerHeight: 31, transform: nil))
    ctx.clip()
    // The image draws into a flipped context, so flip it back.
    ctx.translateBy(x: 0, y: rect.midY * 2)
    ctx.scaleBy(x: 1, y: -1)
    ctx.draw(icon, in: rect)
    ctx.restoreGState()
}

// --- text ------------------------------------------------------------------
func draw(_ text: String, font: CTFont, color: CGColor, x: Double, top: Double,
          tracking: Double = 0) {
    // CoreText keys, not AppKit's — this is a Foundation-only script.
    var attrs: [NSAttributedString.Key: Any] = [
        kCTFontAttributeName as NSAttributedString.Key: font,
        kCTForegroundColorAttributeName as NSAttributedString.Key: color,
    ]
    if tracking != 0 { attrs[kCTKernAttributeName as NSAttributedString.Key] = tracking }
    let line = CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: attrs))
    var ascent = CGFloat(0), descent = CGFloat(0), leading = CGFloat(0)
    CTLineGetTypographicBounds(line, &ascent, &descent, &leading)

    ctx.saveGState()
    // Undo the global flip just for glyph drawing, then position by baseline.
    ctx.translateBy(x: 0, y: H)
    ctx.scaleBy(x: 1, y: -1)
    ctx.textPosition = CGPoint(x: x, y: H - top - Double(ascent))
    CTLineDraw(line, ctx)
    ctx.restoreGState()
}

let wordmark = CTFontCreateWithName("Georgia-Bold" as CFString, 62, nil)
let headline = CTFontCreateWithName("HelveticaNeue-Bold" as CFString, 46, nil)
let subline  = CTFontCreateWithName("HelveticaNeue" as CFString, 27, nil)
let eyebrow  = CTFontCreateWithName("HelveticaNeue-Medium" as CFString, 21, nil)

draw("Milesta", font: wordmark, color: ink, x: 238, top: 90, tracking: -0.8)
draw("iOS · 15 languages · nothing leaves your phone",
     font: eyebrow, color: accent, x: 241, top: 164, tracking: 0.4)

draw("Your life, one milestone",  font: headline, color: ink, x: 72, top: 244, tracking: -0.6)
draw("at a time.",                font: headline, color: ink, x: 72, top: 298, tracking: -0.6)
draw("A private life journal that turns your biggest moments",
     font: subline, color: inkSoft, x: 72, top: 372)
draw("into a beautiful, scrollable path.",
     font: subline, color: inkSoft, x: 72, top: 408)

// --- write -----------------------------------------------------------------
guard let image = ctx.makeImage(),
      let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: outPath) as CFURL,
                                                 UTType.png.identifier as CFString, 1, nil) else {
    fatalError("could not encode")
}
CGImageDestinationAddImage(dest, image, nil)
guard CGImageDestinationFinalize(dest) else { fatalError("could not write \(outPath)") }
print("wrote \(outPath) \(Int(W))x\(Int(H))")

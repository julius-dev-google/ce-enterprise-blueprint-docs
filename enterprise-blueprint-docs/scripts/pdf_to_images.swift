import Foundation
import PDFKit
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 3 else {
    print("Usage: swift pdf_to_images.swift <input.pdf> <output_dir> [scale]")
    exit(1)
}

let pdfPath = args[1]
let outputDir = args[2]
let scale: CGFloat = args.count >= 4 ? CGFloat(Double(args[3]) ?? 2.0) : 2.0

let fileURL = URL(fileURLWithPath: pdfPath)
guard let pdfDocument = PDFDocument(url: fileURL) else {
    print("Failed to load PDF document: \(pdfPath)")
    exit(1)
}

let fileManager = FileManager.default
try? fileManager.createDirectory(atPath: outputDir, withIntermediateDirectories: true)

let pageCount = pdfDocument.pageCount
print("PDF has \(pageCount) pages. Rendering each page to PNG at \(scale)x...")

for pageIndex in 0..<pageCount {
    guard let page = pdfDocument.page(at: pageIndex) else { continue }
    let pageBounds = page.bounds(for: .mediaBox)
    
    let width = Int(pageBounds.width * scale)
    let height = Int(pageBounds.height * scale)
    
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    let bitmapInfo = CGImageAlphaInfo.premultipliedLast.rawValue
    
    guard let context = CGContext(
        data: nil,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: colorSpace,
        bitmapInfo: bitmapInfo
    ) else {
        print("Failed to create CGContext for page \(pageIndex + 1)")
        continue
    }
    
    // Fill white background
    context.setFillColor(CGColor(red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0))
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    
    context.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context)
    
    guard let cgImage = context.makeImage() else {
        print("Failed to make image for page \(pageIndex + 1)")
        continue
    }
    
    let outURL = URL(fileURLWithPath: "\(outputDir)/page_\(pageIndex + 1).png")
    guard let destination = CGImageDestinationCreateWithURL(outURL as CFURL, UTType.png.identifier as CFString, 1, nil) else {
        print("Failed to create image destination for page \(pageIndex + 1)")
        continue
    }
    
    CGImageDestinationAddImage(destination, cgImage, nil)
    if CGImageDestinationFinalize(destination) {
        print("Rendered page \(pageIndex + 1)/\(pageCount) -> \(outURL.path)")
    }
}
print("Done rendering all pages.")

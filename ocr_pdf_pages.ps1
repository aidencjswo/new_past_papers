param(
  [string]$ImageDir = "$PSScriptRoot\samples",
  [string]$OutDir = "$PSScriptRoot\ocr_results"
)

# Load WinRT assemblies
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() |
  Where-Object {
    $_.Name -eq 'AsTask' -and
    $_.IsGenericMethodDefinition -and
    $_.GetGenericArguments().Count -eq 1 -and
    $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
  } |
  Select-Object -First 1

function Await-Typed($operation, [Type]$resultType) {
  $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
  return $task.GetAwaiter().GetResult()
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('ko'))
if ($null -eq $engine) {
  Write-Error "Korean OCR engine is not available on this Windows installation."
  exit 1
}

if (!(Test-Path -Path $OutDir)) {
  New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$files = Get-ChildItem -LiteralPath $ImageDir -Filter "*.png" | Sort-Object Name
$total = $files.Count
$index = 0

foreach ($file in $files) {
  $index += 1
  Write-Host "OCR-ing image: $($file.Name) ($index / $total)"
  
  try {
    $storageFile = Await-Typed ([Windows.Storage.StorageFile]::GetFileFromPathAsync($file.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await-Typed ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await-Typed ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-Typed ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await-Typed ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    
    $lines = @()
    foreach ($line in $result.Lines) {
      $words = @()
      $minX = 99999
      $minY = 99999
      $maxX = 0
      $maxY = 0
      
      foreach ($word in $line.Words) {
        $rect = $word.BoundingRect
        if ($rect.X -lt $minX) { $minX = $rect.X }
        if ($rect.Y -lt $minY) { $minY = $rect.Y }
        if (($rect.X + $rect.Width) -gt $maxX) { $maxX = ($rect.X + $rect.Width) }
        if (($rect.Y + $rect.Height) -gt $maxY) { $maxY = ($rect.Y + $rect.Height) }
        
        $words += @{
          text = $word.Text
          box = @{
            x = $rect.X
            y = $rect.Y
            w = $rect.Width
            h = $rect.Height
          }
        }
      }
      
      $width = $maxX - $minX
      $height = $maxY - $minY
      
      $lines += @{
        text = $line.Text
        box = @{
          x = $minX
          y = $minY
          w = $width
          h = $height
        }
        words = $words
      }
    }
    
    $outObj = @{
      file = $file.Name
      width = $bitmap.PixelWidth
      height = $bitmap.PixelHeight
      lines = $lines
    }
    
    $outName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name) + "_ocr.json"
    $outPath = Join-Path -Path $OutDir -ChildPath $outName
    
    $outObj | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outPath -Encoding UTF8
  } catch {
    Write-Error "Failed to process $($file.Name): $_"
  }
}

Write-Host "Completed OCR for all images. Results in $OutDir"

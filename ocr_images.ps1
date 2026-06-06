param(
  [string]$ImageDir = "$PSScriptRoot\ocr_images",
  [string]$OutFile = "$PSScriptRoot\ocr_raw.json"
)

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

function Read-OcrText([string]$path, $engine) {
  try {
    $file = Await-Typed ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
    $stream = Await-Typed ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await-Typed ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-Typed ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await-Typed ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    return $result.Text
  } catch {
    return ""
  }
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('ko'))
if ($null -eq $engine) {
  throw "Korean OCR engine is not available on this Windows installation."
}

$items = @()
$files = Get-ChildItem -LiteralPath $ImageDir -File | Sort-Object Name
$total = $files.Count
$index = 0

foreach ($file in $files) {
  $index += 1
  Write-Progress -Activity "OCR images" -Status "$index / $total" -PercentComplete (($index / $total) * 100)
  $text = Read-OcrText $file.FullName $engine
  $page = 0
  $imageIndex = 0
  if ($file.Name -match 'page_(\d+)_image_(\d+)') {
    $page = [int]$Matches[1]
    $imageIndex = [int]$Matches[2]
  }
  $items += [pscustomobject]@{
    page = $page
    imageIndex = $imageIndex
    file = $file.Name
    text = $text
  }
}

$items | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "wrote $OutFile"

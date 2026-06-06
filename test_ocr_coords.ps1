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

$path = "$PSScriptRoot\samples\2018_page_1.png"
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('ko'))

if ($null -eq $engine) {
  Write-Host "Korean OCR not available"
  exit
}

$file = Await-Typed ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
$stream = Await-Typed ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await-Typed ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await-Typed ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$result = Await-Typed ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

Write-Host "Total Lines: $($result.Lines.Count)"
foreach ($line in $result.Lines | Select-Object -First 15) {
    # Calculate bounding box of the line by looking at its words
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
    }
    $width = $maxX - $minX
    $height = $maxY - $minY
    Write-Host "Line: '$($line.Text)' -> Box: X=$minX, Y=$minY, W=$width, H=$height"
}

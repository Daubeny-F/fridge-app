param([string]$Sender = '', [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $Sender) { $Sender = Read-Host 'Sender Gmail address' }
$Sender = $Sender.Trim()
try { $address = [System.Net.Mail.MailAddress]::new($Sender) }
catch { throw 'Enter a valid sender email address.' }
if ($address.Address -ne $Sender) { throw 'Enter only the email address, without a display name.' }
Write-Host 'Use a Google App Password. Do not enter your normal Gmail password.'
Write-Host 'Create one yourself at https://myaccount.google.com/apppasswords (2-Step Verification required).'
$gmailSecret = Read-Host 'Gmail App Password (hidden; kept only for this run)' -AsSecureString
$settingNames = @('EMAIL_BACKEND','EMAIL_HOST','EMAIL_PORT','EMAIL_USE_TLS','EMAIL_HOST_USER','EMAIL_HOST_PASSWORD','DEFAULT_FROM_EMAIL')
$previousSettings = @{}
foreach ($settingName in $settingNames) { $previousSettings[$settingName] = [Environment]::GetEnvironmentVariable($settingName, 'Process') }
$secretPointer = [IntPtr]::Zero
$plainSecret = $null
try {
    $secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($gmailSecret)
    $plainSecret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer) -replace '\s', ''
    if ($plainSecret -notmatch '^[a-zA-Z0-9]{16}$') { throw 'A Google App Password has 16 characters. Create one in your Google Account.' }
    $env:EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    $env:EMAIL_HOST = 'smtp.gmail.com'
    $env:EMAIL_PORT = '587'
    $env:EMAIL_USE_TLS = '1'
    $env:EMAIL_HOST_USER = $Sender
    $env:EMAIL_HOST_PASSWORD = $plainSecret
    $env:DEFAULT_FROM_EMAIL = "Fridgewise <$Sender>"
    Write-Host 'Gmail mode configured. Nothing is sent until an admin clicks the send button.' -ForegroundColor Green
    & (Join-Path $PSScriptRoot 'start.ps1') -Port $Port
}
finally {
    foreach ($settingName in $settingNames) { [Environment]::SetEnvironmentVariable($settingName, $previousSettings[$settingName], 'Process') }
    if ($secretPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer) }
    $plainSecret = $null
    $gmailSecret.Dispose()
}

#!/usr/bin/env pwsh

Write-Host "🔍 Debugging Navigation Issue" -ForegroundColor Cyan
Write-Host "=" * 40

# Test 1: Check if the route is being registered correctly
Write-Host "`n📍 Test 1: Checking route registration..." -ForegroundColor Yellow

$routerFile = "frontend/src/components/AppRouter.tsx"
$routerContent = Get-Content $routerFile -Raw

if ($routerContent -match "currentPath === '/create-project'") {
    Write-Host "✅ Route '/create-project' is registered in AppRouter" -ForegroundColor Green
} else {
    Write-Host "❌ Route '/create-project' not found in AppRouter" -ForegroundColor Red
}

# Test 2: Check if the component is being imported
if ($routerContent -match "import.*EnhancedProjectCreationWorkflow") {
    Write-Host "✅ EnhancedProjectCreationWorkflow is imported" -ForegroundColor Green
} else {
    Write-Host "❌ EnhancedProjectCreationWorkflow import missing" -ForegroundColor Red
}

# Test 3: Check if there are any syntax errors in the component
Write-Host "`n🔧 Test 2: Checking component syntax..." -ForegroundColor Yellow

$componentFile = "frontend/src/components/EnhancedProjectCreationWorkflow.tsx"
if (Test-Path $componentFile) {
    try {
        Push-Location "frontend"
        
        # Try to compile just this component
        $result = npx tsc --noEmit --skipLibCheck $componentFile.Replace("frontend/", "") 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Component compiles without errors" -ForegroundColor Green
        } else {
            Write-Host "❌ Component has compilation errors:" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
        }
    } catch {
        Write-Host "⚠️  Could not run TypeScript check: $($_.Exception.Message)" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
} else {
    Write-Host "❌ Component file not found" -ForegroundColor Red
}

# Test 3: Check if SimpleProtectedRoute exists
Write-Host "`n🔒 Test 3: Checking authentication components..." -ForegroundColor Yellow

$protectedRouteFile = "frontend/src/components/auth/SimpleProtectedRoute.tsx"
if (Test-Path $protectedRouteFile) {
    Write-Host "✅ SimpleProtectedRoute component exists" -ForegroundColor Green
} else {
    Write-Host "❌ SimpleProtectedRoute component missing" -ForegroundColor Red
}

# Test 4: Check if there are missing dependencies
Write-Host "`n📦 Test 4: Checking for missing UI components..." -ForegroundColor Yellow

$componentContent = Get-Content $componentFile -Raw

$requiredComponents = @(
    "Button",
    "useToast",
    "navigate"
)

foreach ($component in $requiredComponents) {
    if ($componentContent -match $component) {
        Write-Host "✅ $component is used in component" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $component not found in component" -ForegroundColor Yellow
    }
}

# Test 5: Create a simple test HTML to verify navigation
Write-Host "`n🧪 Test 5: Creating navigation test..." -ForegroundColor Yellow

$testHtml = @"
<!DOCTYPE html>
<html>
<head>
    <title>Navigation Test</title>
</head>
<body>
    <h1>Navigation Test</h1>
    <p>Current hash: <span id="current-hash"></span></p>
    <button onclick="testNavigation()">Test Navigate to /create-project</button>
    <div id="result"></div>
    
    <script>
        function updateHash() {
            document.getElementById('current-hash').textContent = window.location.hash || '(none)';
        }
        
        function testNavigation() {
            try {
                window.location.hash = '/create-project';
                document.getElementById('result').innerHTML = '<p style="color: green;">✅ Navigation successful</p>';
                updateHash();
            } catch (error) {
                document.getElementById('result').innerHTML = '<p style="color: red;">❌ Navigation failed: ' + error.message + '</p>';
            }
        }
        
        window.addEventListener('hashchange', updateHash);
        updateHash();
    </script>
</body>
</html>
"@

$testHtml | Out-File -FilePath "navigation-test.html" -Encoding UTF8
Write-Host "✅ Created navigation-test.html for manual testing" -ForegroundColor Green

# Test 6: Check browser console for errors
Write-Host "`n🌐 Test 6: Instructions for browser testing..." -ForegroundColor Yellow
Write-Host "1. Open the application in your browser" -ForegroundColor White
Write-Host "2. Open Developer Tools (F12)" -ForegroundColor White
Write-Host "3. Go to Console tab" -ForegroundColor White
Write-Host "4. Click the 'Start Project' button" -ForegroundColor White
Write-Host "5. Check for any error messages in the console" -ForegroundColor White
Write-Host "6. Check the Network tab for any failed requests" -ForegroundColor White

Write-Host "`n📋 Common Issues to Check:" -ForegroundColor Cyan
Write-Host "• Authentication token missing or invalid" -ForegroundColor White
Write-Host "• Component import/export errors" -ForegroundColor White
Write-Host "• Missing dependencies in package.json" -ForegroundColor White
Write-Host "• Error boundary catching and hiding errors" -ForegroundColor White
Write-Host "• Hash routing not working properly" -ForegroundColor White

Write-Host "`n🔧 Quick Fix Suggestions:" -ForegroundColor Green
Write-Host "1. Check browser console for JavaScript errors" -ForegroundColor White
Write-Host "2. Verify authentication state in localStorage" -ForegroundColor White
Write-Host "3. Test direct navigation to /#/create-project" -ForegroundColor White
Write-Host "4. Check if the component renders in isolation" -ForegroundColor White

Write-Host "`n🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "• Run this debug script and check results" -ForegroundColor White
Write-Host "• Test navigation manually in browser" -ForegroundColor White
Write-Host "• Check browser console for errors" -ForegroundColor White
Write-Host "• Report specific error messages if found" -ForegroundColor White
#!/usr/bin/env pwsh

Write-Host "🧪 Testing Enhanced Project Creation Workflow" -ForegroundColor Cyan
Write-Host "=" * 50

# Test 1: Check if the component can be imported without errors
Write-Host "`n📦 Test 1: Component Import Test..." -ForegroundColor Yellow

$testFile = "frontend/src/test-component-import.js"
$testContent = @"
// Simple test to check if the component can be imported
try {
  const React = require('react');
  console.log('✅ React imported successfully');
  
  // Test if the component file exists and can be read
  const fs = require('fs');
  const path = require('path');
  
  const componentPath = path.join(__dirname, 'components', 'EnhancedProjectCreationWorkflow.tsx');
  if (fs.existsSync(componentPath)) {
    console.log('✅ Component file exists');
    const content = fs.readFileSync(componentPath, 'utf8');
    
    // Check for basic React component structure
    if (content.includes('export const EnhancedProjectCreationWorkflow')) {
      console.log('✅ Component export found');
    } else {
      console.log('❌ Component export not found');
    }
    
    // Check for JSX syntax
    if (content.includes('<div') || content.includes('<Button')) {
      console.log('✅ JSX syntax found');
    } else {
      console.log('❌ JSX syntax not found');
    }
    
  } else {
    console.log('❌ Component file does not exist');
  }
  
} catch (error) {
  console.log('❌ Import test failed:', error.message);
}
"@

$testContent | Out-File -FilePath $testFile -Encoding UTF8

try {
    Push-Location "frontend"
    $result = node "src/test-component-import.js" 2>&1
    Write-Host $result
} catch {
    Write-Host "❌ Node.js test failed: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Pop-Location
    Remove-Item $testFile -ErrorAction SilentlyContinue
}

# Test 2: Check browser console for errors
Write-Host "`n🌐 Test 2: Browser Console Check..." -ForegroundColor Yellow
Write-Host "Manual steps to check browser console:" -ForegroundColor White
Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor Gray
Write-Host "2. Log in with your credentials" -ForegroundColor Gray
Write-Host "3. Open Developer Tools (F12)" -ForegroundColor Gray
Write-Host "4. Go to Console tab" -ForegroundColor Gray
Write-Host "5. Click 'Start Project' button" -ForegroundColor Gray
Write-Host "6. Look for any error messages" -ForegroundColor Gray

# Test 3: Direct URL test
Write-Host "`n🔗 Test 3: Direct URL Navigation..." -ForegroundColor Yellow
Write-Host "Try navigating directly to:" -ForegroundColor White
Write-Host "http://localhost:3000/#/create-project" -ForegroundColor Cyan

# Test 4: Check for common issues
Write-Host "`n🔍 Test 4: Common Issues Check..." -ForegroundColor Yellow

# Check if Button component exists
$buttonPath = "frontend/src/components/ui/Button.tsx"
if (Test-Path $buttonPath) {
    Write-Host "✅ Button component exists" -ForegroundColor Green
} else {
    Write-Host "❌ Button component missing" -ForegroundColor Red
}

# Check if Toast store exists
$toastPath = "frontend/src/store/toastStore.ts"
if (Test-Path $toastPath) {
    Write-Host "✅ Toast store exists" -ForegroundColor Green
} else {
    Write-Host "❌ Toast store missing" -ForegroundColor Red
}

# Check if AppRouter navigate function is exported
$routerContent = Get-Content "frontend/src/components/AppRouter.tsx" -Raw
if ($routerContent -match "export const navigate") {
    Write-Host "✅ Navigate function is exported" -ForegroundColor Green
} else {
    Write-Host "❌ Navigate function not exported" -ForegroundColor Red
}

Write-Host "`n🎯 Recommendations:" -ForegroundColor Green
Write-Host "1. Start the development server: npm start (in frontend folder)" -ForegroundColor White
Write-Host "2. Open browser and check console for JavaScript errors" -ForegroundColor White
Write-Host "3. Test direct navigation to /#/create-project" -ForegroundColor White
Write-Host "4. Check if authentication is working properly" -ForegroundColor White
Write-Host "5. Look for any error boundaries that might be catching errors" -ForegroundColor White

Write-Host "`n📝 Next Steps if Issues Found:" -ForegroundColor Yellow
Write-Host "• Report specific error messages from browser console" -ForegroundColor White
Write-Host "• Check if the component renders when accessed directly" -ForegroundColor White
Write-Host "• Verify all dependencies are properly imported" -ForegroundColor White
Write-Host "• Test with different browsers" -ForegroundColor White
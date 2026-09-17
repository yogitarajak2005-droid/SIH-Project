/**
 * VerifyAI - Frontend Controller
 * Handles document uploads, synthetic demo selection, animated multi-step screening,
 * dynamic risk score gauge rendering, and live analytics dashboard.
 */

document.addEventListener('DOMContentLoaded', () => {
    initUploadCard();
    initDemoDocumentSelector();
    initAdminAnalytics();
    initSmoothNavigation();
});

// Global state
let currentSelectedFile = null;
let distributionChart = null;

/**
 * Upload Card & Drag-and-Drop Management
 */
function initUploadCard() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('document-input');
    const previewContainer = document.getElementById('preview-container');
    const previewImage = document.getElementById('preview-image');
    const previewFilename = document.getElementById('preview-filename');
    const previewFilesize = document.getElementById('preview-filesize');
    const removeFileBtn = document.getElementById('remove-file-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const uploadPrompt = document.getElementById('upload-prompt');

    if (!dropZone || !fileInput) return;

    // Drag-over highlights
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-active');
        }, false);
    });

    // Drop handler
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleSelectedFile(files[0]);
        }
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    // Click to select
    dropZone.addEventListener('click', (e) => {
        if (e.target.closest('#remove-file-btn') || e.target.closest('#analyze-btn')) return;
        fileInput.click();
    });

    // Remove file button
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            clearSelectedFile();
        });
    }

    // Analyze document button
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!currentSelectedFile) {
                showToast('Please select or upload a document to screen.', 'warning');
                return;
            }
            executeScreeningPipeline(currentSelectedFile);
        });
    }
}

/**
 * Validates and displays selected file
 */
function handleSelectedFile(file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    const maxSize = 5 * 1024 * 1024; // 5MB

    if (!validTypes.includes(file.type) && !file.name.match(/\.(jpg|jpeg|png)$/i)) {
        showToast('Unsupported file format. Please upload JPG, JPEG, or PNG.', 'error');
        return;
    }

    if (file.size > maxSize) {
        showToast(`File is larger than 5 MB (${(file.size / (1024 * 1024)).toFixed(2)} MB).`, 'error');
        return;
    }

    currentSelectedFile = file;

    // Update UI Preview
    const previewContainer = document.getElementById('preview-container');
    const uploadPrompt = document.getElementById('upload-prompt');
    const previewImage = document.getElementById('preview-image');
    const previewFilename = document.getElementById('preview-filename');
    const previewFilesize = document.getElementById('preview-filesize');
    const analyzeBtn = document.getElementById('analyze-btn');

    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        previewFilename.textContent = file.name;
        previewFilesize.textContent = (file.size / 1024).toFixed(1) + ' KB';

        uploadPrompt.classList.add('hidden');
        previewContainer.classList.remove('hidden');
        analyzeBtn.disabled = false;
        analyzeBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    };
    reader.readAsDataURL(file);

    showToast(`Loaded: ${file.name}`, 'info');
}

/**
 * Clears current selected document
 */
function clearSelectedFile() {
    currentSelectedFile = null;
    const fileInput = document.getElementById('document-input');
    const previewContainer = document.getElementById('preview-container');
    const uploadPrompt = document.getElementById('upload-prompt');
    const analyzeBtn = document.getElementById('analyze-btn');

    if (fileInput) fileInput.value = '';
    if (previewContainer) previewContainer.classList.add('hidden');
    if (uploadPrompt) uploadPrompt.classList.remove('hidden');
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }
}

/**
 * Preset synthetic demo document loader
 */
function initDemoDocumentSelector() {
    const demoButtons = document.querySelectorAll('.demo-doc-btn');
    demoButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const docType = btn.getAttribute('data-demo-type');
            await loadSyntheticSample(docType);
        });
    });
}

/**
 * Loads a synthetic demo document from /static/samples/
 */
async function loadSyntheticSample(type) {
    let filename = 'sample_valid.png';
    let label = 'Synthetic_Clean_Document.png';

    if (type === 'blurry') {
        filename = 'sample_blurry.png';
        label = 'Synthetic_Blurry_Document.png';
    } else if (type === 'inconsistent') {
        filename = 'sample_inconsistent.png';
        label = 'Synthetic_Inconsistent_Document.png';
    }

    const sampleUrl = `/static/samples/${filename}`;

    try {
        showToast(`Loading demo document: ${label}...`, 'info');
        const response = await fetch(sampleUrl);
        if (!response.ok) throw new Error('Could not fetch synthetic demo document');

        const blob = await response.blob();
        const demoFile = new File([blob], label, { type: 'image/png' });

        handleSelectedFile(demoFile);

        // Auto-scroll slightly to show uploaded file
        document.getElementById('screening-dashboard').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        console.error('Demo load error:', err);
        showToast('Error loading synthetic sample document.', 'error');
    }
}

/**
 * Multi-Stage Animated Processing & API Execution
 */
async function executeScreeningPipeline(file) {
    const progressModal = document.getElementById('progress-card');
    const resultSection = document.getElementById('result-section');
    const analyzeBtn = document.getElementById('analyze-btn');

    // UI state transitions
    if (analyzeBtn) analyzeBtn.disabled = true;
    if (progressModal) {
        progressModal.classList.remove('hidden');
        progressModal.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (resultSection) resultSection.classList.add('hidden');

    const steps = [
        { id: 'step-1', text: 'Uploading document...', delay: 350 },
        { id: 'step-2', text: 'Preprocessing image (OpenCV)...', delay: 450 },
        { id: 'step-3', text: 'Extracting text via OCR...', delay: 500 },
        { id: 'step-4', text: 'Checking consistency & format...', delay: 400 },
        { id: 'step-5', text: 'Generating explainable screening result...', delay: 350 }
    ];

    // Reset step indicators
    steps.forEach(s => {
        const el = document.getElementById(s.id);
        if (el) {
            el.className = 'flex items-center gap-3 p-3 rounded-lg border border-slate-800 bg-slate-900/40 text-slate-400 transition-all duration-300';
            const icon = el.querySelector('.step-icon');
            if (icon) icon.innerHTML = '<i class="fas fa-circle-notch text-xs text-slate-500"></i>';
        }
    });

    const progressBar = document.getElementById('pipeline-progress-bar');
    if (progressBar) progressBar.style.width = '5%';

    // Launch backend fetch concurrently
    const formData = new FormData();
    formData.append('document', file);

    const csrfToken = getCookie('csrftoken');
    const headers = {};
    if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
    }

    let fetchResult = null;
    let fetchError = null;

    const fetchPromise = fetch('/api/screen/', {
        method: 'POST',
        headers: headers,
        body: formData
    })
    .then(async res => {
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || `Server responded with HTTP ${res.status}`);
        }
        return data;
    })
    .catch(err => {
        fetchError = err.message;
    });

    // Animate through the 5 steps smoothly
    for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        const stepEl = document.getElementById(step.id);
        const pct = Math.round(((i + 1) / steps.length) * 100);

        if (stepEl) {
            stepEl.className = 'flex items-center gap-3 p-3 rounded-lg border border-cyan-500/50 bg-cyan-950/20 text-cyan-300 shadow-sm shadow-cyan-500/10 transition-all duration-300';
            const icon = stepEl.querySelector('.step-icon');
            if (icon) icon.innerHTML = '<i class="fas fa-spinner fa-spin text-cyan-400"></i>';
        }

        if (progressBar) progressBar.style.width = `${pct}%`;
        await new Promise(r => setTimeout(r, step.delay));

        if (stepEl) {
            stepEl.className = 'flex items-center gap-3 p-3 rounded-lg border border-emerald-500/30 bg-emerald-950/20 text-emerald-300 transition-all duration-300';
            const icon = stepEl.querySelector('.step-icon');
            if (icon) icon.innerHTML = '<i class="fas fa-check-circle text-emerald-400"></i>';
        }
    }

    // Await actual API response
    await fetchPromise;

    if (analyzeBtn) analyzeBtn.disabled = false;
    if (progressModal) progressModal.classList.add('hidden');

    if (fetchError) {
        showToast(fetchError, 'error');
        return;
    }

    // Render results
    renderScreeningResults(await fetchPromise);
}

/**
 * Dynamically populates and reveals the Screening Result Dashboard
 */
function renderScreeningResults(data) {
    const resultSection = document.getElementById('result-section');
    if (!resultSection || !data) return;

    resultSection.classList.remove('hidden');

    const score = data.screening.risk_score;
    const level = data.screening.risk_level;
    const summary = data.screening.summary;
    const extracted = data.extracted_data;
    const flags = data.screening.detailed_flags || [];
    const breakdown = data.breakdown || {};

    // 1. Risk Score & Gauge Rendering
    const scoreValEl = document.getElementById('risk-score-value');
    const scoreLevelBadge = document.getElementById('risk-level-badge');
    const scoreSummaryEl = document.getElementById('risk-score-summary');
    const gaugeCircle = document.getElementById('gauge-progress');

    if (scoreValEl) scoreValEl.textContent = `${score}/100`;
    if (scoreSummaryEl) scoreSummaryEl.textContent = summary;

    // Circumference = 2 * PI * 54 = ~339.29
    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (score / 100) * circumference;

    if (gaugeCircle) {
        gaugeCircle.style.strokeDasharray = `${circumference} ${circumference}`;
        gaugeCircle.style.strokeDashoffset = offset;

        // Color coding
        if (score <= 30) {
            gaugeCircle.style.stroke = '#10B981'; // Emerald
        } else if (score <= 65) {
            gaugeCircle.style.stroke = '#F59E0B'; // Amber
        } else {
            gaugeCircle.style.stroke = '#F43F5E'; // Rose
        }
    }

    // Risk Level Badge Styling
    if (scoreLevelBadge) {
        scoreLevelBadge.textContent = level;
        scoreLevelBadge.className = 'px-4 py-1.5 rounded-full font-bold text-sm tracking-wider uppercase inline-flex items-center gap-2 ';
        if (score <= 30) {
            scoreLevelBadge.classList.add('badge-low');
            scoreLevelBadge.innerHTML = '<i class="fas fa-shield-check"></i> ' + level;
        } else if (score <= 65) {
            scoreLevelBadge.classList.add('badge-medium');
            scoreLevelBadge.innerHTML = '<i class="fas fa-shield-halved"></i> ' + level;
        } else {
            scoreLevelBadge.classList.add('badge-high');
            scoreLevelBadge.innerHTML = '<i class="fas fa-shield-exclamation"></i> ' + level;
        }
    }

    // 2. Extracted Information Fields
    const nameEl = document.getElementById('extracted-name');
    const dobEl = document.getElementById('extracted-dob');
    const idEl = document.getElementById('extracted-id');
    const genderEl = document.getElementById('extracted-gender');
    const datesEl = document.getElementById('extracted-dates');
    const ocrSnippetEl = document.getElementById('ocr-raw-snippet');

    if (nameEl) nameEl.textContent = extracted.name || 'Not detected';
    if (dobEl) dobEl.textContent = extracted.dob || 'Not detected';
    if (idEl) idEl.textContent = extracted.document_id || 'Not detected';
    if (genderEl) genderEl.textContent = extracted.gender || 'Not specified';
    if (datesEl) datesEl.textContent = `Issue: ${extracted.issue_date || 'N/A'} • Exp: ${extracted.expiry_date || 'N/A'}`;
    if (ocrSnippetEl) ocrSnippetEl.textContent = data.ocr_text || '(No OCR text extracted)';

    // 3. Detected Review Flags
    const flagsContainer = document.getElementById('review-flags-container');
    if (flagsContainer) {
        flagsContainer.innerHTML = '';
        if (flags.length === 0) {
            flagsContainer.innerHTML = `
                <div class="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-emerald-300 flex items-center gap-3">
                    <i class="fas fa-check-double text-emerald-400 text-lg"></i>
                    <span>No anomaly flags detected. Document passes initial baseline screening.</span>
                </div>
            `;
        } else {
            flags.forEach(flag => {
                const flagCard = document.createElement('div');
                let borderClass = 'border-slate-800 bg-slate-900/50';
                let iconColor = 'text-cyan-400';
                let pillClass = 'bg-slate-800 text-slate-300 border-slate-700';

                if (flag.severity === 'high') {
                    borderClass = 'border-rose-500/30 bg-rose-950/20';
                    iconColor = 'text-rose-400';
                    pillClass = 'bg-rose-950/40 text-rose-300 border-rose-500/40';
                } else if (flag.severity === 'medium') {
                    borderClass = 'border-amber-500/30 bg-amber-950/20';
                    iconColor = 'text-amber-400';
                    pillClass = 'bg-amber-950/40 text-amber-300 border-amber-500/40';
                } else if (flag.severity === 'info') {
                    borderClass = 'border-emerald-500/30 bg-emerald-950/20';
                    iconColor = 'text-emerald-400';
                    pillClass = 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40';
                }

                flagCard.className = `p-4 rounded-xl border ${borderClass} flex items-start justify-between gap-4 transition-all`;
                flagCard.innerHTML = `
                    <div class="flex items-start gap-3">
                        <div class="mt-0.5"><i class="fas fa-${flag.icon || 'exclamation-circle'} ${iconColor} text-lg"></i></div>
                        <div>
                            <h4 class="font-semibold text-white text-sm">${flag.title || 'Screening Flag'}</h4>
                            <p class="text-xs text-slate-300 mt-0.5 leading-relaxed">${flag.explanation}</p>
                        </div>
                    </div>
                    <span class="px-2.5 py-0.5 text-xs rounded-full border uppercase font-mono font-semibold tracking-wider whitespace-nowrap ${pillClass}">
                        ${flag.severity}
                    </span>
                `;
                flagsContainer.appendChild(flagCard);
            });
        }
    }

    // 4. Analysis Breakdown (4 Cards)
    // Card 1: OCR Analysis
    const ocrData = breakdown.ocr_analysis || {};
    const ocrStatusEl = document.getElementById('breakdown-ocr-status');
    const ocrConfEl = document.getElementById('breakdown-ocr-confidence');
    const ocrEngineEl = document.getElementById('breakdown-ocr-engine');
    const ocrYieldEl = document.getElementById('breakdown-ocr-yield');

    if (ocrStatusEl) ocrStatusEl.textContent = ocrData.status || 'Active';
    if (ocrConfEl) ocrConfEl.textContent = `${ocrData.confidence_score || 0}%`;
    if (ocrEngineEl) ocrEngineEl.textContent = ocrData.engine || 'OCR Engine';
    if (ocrYieldEl) ocrYieldEl.textContent = `${ocrData.word_count || 0} words / ${ocrData.character_count || 0} chars`;

    // Card 2: Document Quality
    const qualityData = breakdown.document_quality || {};
    const qualBlurEl = document.getElementById('breakdown-quality-blur');
    const qualContrastEl = document.getElementById('breakdown-quality-contrast');
    const qualResEl = document.getElementById('breakdown-quality-resolution');
    const qualRatioEl = document.getElementById('breakdown-quality-ratio');

    if (qualBlurEl) {
        qualBlurEl.textContent = qualityData.is_blurry ? `Blurry (Score: ${qualityData.blur_score})` : `Sharp (Score: ${qualityData.blur_score})`;
        qualBlurEl.className = qualityData.is_blurry ? 'font-mono text-rose-400 font-semibold' : 'font-mono text-emerald-400 font-semibold';
    }
    if (qualContrastEl) qualContrastEl.textContent = `Contrast StdDev: ${qualityData.contrast_score || 'N/A'}`;
    if (qualResEl) qualResEl.textContent = qualityData.resolution || 'Standard';
    if (qualRatioEl) qualRatioEl.textContent = `Aspect: ${qualityData.aspect_ratio}:1 (${qualityData.aspect_ratio_valid ? 'Valid Card' : 'Non-standard'})`;

    // Card 3: Consistency Checks
    const consData = breakdown.consistency_checks || {};
    const consFieldsEl = document.getElementById('breakdown-cons-fields');
    const consDateEl = document.getElementById('breakdown-cons-date');
    const consPatternEl = document.getElementById('breakdown-cons-patterns');

    if (consFieldsEl) {
        consFieldsEl.textContent = consData.required_fields_present ? 'All Required Present' : `Missing: ${consData.missing_fields?.join(', ') || 'Fields'}`;
        consFieldsEl.className = consData.required_fields_present ? 'font-semibold text-emerald-400' : 'font-semibold text-rose-400';
    }
    if (consDateEl) {
        consDateEl.textContent = (consData.date_format_valid && consData.date_reasonableness) ? 'Date Format Valid' : 'Date Format Requires Review';
        consDateEl.className = (consData.date_format_valid && consData.date_reasonableness) ? 'font-semibold text-emerald-400' : 'font-semibold text-amber-400';
    }
    if (consPatternEl) {
        consPatternEl.textContent = (consData.suspicious_characters || consData.unusual_patterns) ? 'Suspicious Characters Detected' : 'No Unusual Patterns';
        consPatternEl.className = (consData.suspicious_characters || consData.unusual_patterns) ? 'font-semibold text-rose-400' : 'font-semibold text-emerald-400';
    }

    // Card 4: Risk Assessment
    const riskScoreBreakEl = document.getElementById('breakdown-risk-score');
    const riskLevelBreakEl = document.getElementById('breakdown-risk-level');
    const riskTimeEl = document.getElementById('breakdown-risk-time');

    if (riskScoreBreakEl) riskScoreBreakEl.textContent = `${score}/100`;
    if (riskLevelBreakEl) riskLevelBreakEl.textContent = level;
    if (riskTimeEl) riskTimeEl.textContent = `${data.processing_time_ms} ms`;

    // Smooth scroll down to view the screening results
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Refresh admin analytics so live screened logs reflect in the table
    refreshAdminStats();
}

/**
 * Admin / Analytics Dashboard Loader & Chart.js Visualizations
 */
async function initAdminAnalytics() {
    await refreshAdminStats();
}

async function refreshAdminStats() {
    try {
        const response = await fetch('/api/stats/');
        if (!response.ok) return;
        const data = await response.json();

        // Update Stat Badges
        const totalEl = document.getElementById('stat-total-screened');
        const lowEl = document.getElementById('stat-low-review');
        const medEl = document.getElementById('stat-medium-review');
        const highEl = document.getElementById('stat-high-review');

        if (totalEl) totalEl.textContent = data.metrics.total_screened;
        if (lowEl) lowEl.textContent = data.metrics.low_review;
        if (medEl) medEl.textContent = data.metrics.medium_review;
        if (highEl) highEl.textContent = data.metrics.high_review;

        // Render Distribution Doughnut Chart
        renderDistributionChart(data.metrics);

        // Populate Recent Screening Table
        populateActivityTable(data.recent_activity);
    } catch (e) {
        console.warn('Analytics stats fetch error:', e);
    }
}

function renderDistributionChart(metrics) {
    const ctx = document.getElementById('risk-distribution-chart');
    if (!ctx) return;

    if (distributionChart) {
        distributionChart.destroy();
    }

    distributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Low Review', 'Medium Review', 'High Review'],
            datasets: [{
                data: [metrics.low_review, metrics.medium_review, metrics.high_review],
                backgroundColor: ['#10B981', '#F59E0B', '#F43F5E'],
                borderWidth: 2,
                borderColor: '#0b1120',
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Plus Jakarta Sans', size: 12 },
                        padding: 16,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(56, 189, 248, 0.3)',
                    borderWidth: 1,
                    padding: 10
                }
            },
            cutout: '70%'
        }
    });
}

function populateActivityTable(records) {
    const tbody = document.getElementById('recent-activity-tbody');
    if (!tbody || !records) return;

    tbody.innerHTML = '';
    records.forEach(rec => {
        const row = document.createElement('tr');
        row.className = 'border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors text-xs font-mono';

        let badgeClass = 'text-emerald-400 bg-emerald-950/40 border border-emerald-500/30';
        if (rec.risk_level === 'MEDIUM REVIEW') {
            badgeClass = 'text-amber-400 bg-amber-950/40 border border-amber-500/30';
        } else if (rec.risk_level === 'HIGH REVIEW') {
            badgeClass = 'text-rose-400 bg-rose-950/40 border border-rose-500/30';
        }

        row.innerHTML = `
            <td class="py-3 px-4 text-slate-400 font-sans">${rec.date}</td>
            <td class="py-3 px-4 font-semibold text-slate-200">${rec.document_type}</td>
            <td class="py-3 px-4 text-cyan-400">${rec.extracted_id}</td>
            <td class="py-3 px-4 font-bold ${rec.risk_score <= 30 ? 'text-emerald-400' : rec.risk_score <= 65 ? 'text-amber-400' : 'text-rose-400'}">${rec.risk_score}/100</td>
            <td class="py-3 px-4">
                <span class="px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase ${badgeClass}">
                    ${rec.risk_level}
                </span>
            </td>
            <td class="py-3 px-4 text-slate-300 font-sans">${rec.review_status}</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Smooth navigation scroll helper
 */
function initSmoothNavigation() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const targetEl = document.querySelector(targetId);
            if (targetEl) {
                e.preventDefault();
                targetEl.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

/**
 * Toast Notification Utility
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    let colorClasses = 'border-cyan-500/40 bg-slate-900/95 text-cyan-300 shadow-cyan-500/20';
    let icon = 'fa-info-circle';

    if (type === 'error') {
        colorClasses = 'border-rose-500/40 bg-slate-900/95 text-rose-300 shadow-rose-500/20';
        icon = 'fa-exclamation-circle';
    } else if (type === 'warning') {
        colorClasses = 'border-amber-500/40 bg-slate-900/95 text-amber-300 shadow-amber-500/20';
        icon = 'fa-exclamation-triangle';
    } else if (type === 'success') {
        colorClasses = 'border-emerald-500/40 bg-slate-900/95 text-emerald-300 shadow-emerald-500/20';
        icon = 'fa-check-circle';
    }

    toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-xl text-sm transition-all duration-300 transform translate-y-2 opacity-0 ${colorClasses}`;
    toast.innerHTML = `
        <i class="fas ${icon} text-base"></i>
        <span class="flex-1">${message}</span>
        <button class="text-slate-400 hover:text-white transition-colors" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 20);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

/**
 * Extracts Django CSRF cookie value
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

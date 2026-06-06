// Smart Question Solver Application Logic
const originalQuestions = window.QUESTIONS || [];

const state = {
  year: null,
  subject: null,
  filter: "all",
  query: "",
  index: 0,
  shuffledIndices: [],
  isShuffled: false,
  userAnswers: JSON.parse(localStorage.getItem("exam-study-answers") || "{}"),
  done: JSON.parse(localStorage.getItem("exam-study-done") || "{}"),
};

// DOM helper
const $ = (id) => document.getElementById(id);

// --- Initialization ---
function init() {
  if (originalQuestions.length === 0) {
    $("titleLabel").textContent = "데이터가 없습니다. PDF를 기출문제 폴더에 넣고 build_questions.py를 실행하세요.";
    return;
  }

  // Extract unique years and subjects
  const years = [...new Set(originalQuestions.map(q => q.year))].sort((a, b) => b - a);
  const subjects = [...new Set(originalQuestions.map(q => q.subject))].sort();

  // Populate selectors
  const yearSelect = $("yearSelect");
  yearSelect.innerHTML = "";
  years.forEach(y => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = `${y}학년도`;
    yearSelect.appendChild(opt);
  });

  const subjectSelect = $("subjectSelect");
  subjectSelect.innerHTML = "";
  subjects.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    subjectSelect.appendChild(opt);
  });

  // Set default state
  state.year = years[0];
  state.subject = subjects[0];

  // Event Listeners for Selectors
  yearSelect.addEventListener("change", (e) => {
    state.year = parseInt(e.target.value);
    resetIndexAndFilter();
  });

  subjectSelect.addEventListener("change", (e) => {
    state.subject = e.target.value;
    resetIndexAndFilter();
  });

  // Search Input
  $("searchInput").addEventListener("input", (e) => {
    state.query = e.target.value.trim().toLowerCase();
    updateFilteredList();
    state.index = 0;
    render();
  });

  // Filter Buttons
  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-filter]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.filter = button.dataset.filter;
      state.index = 0;
      updateFilteredList();
      render();
    });
  });

  // Navigation Buttons
  $("prevBtn").addEventListener("click", () => move(-1));
  $("nextBtn").addEventListener("click", () => move(1));

  // Action Buttons
  $("doneBtn").addEventListener("click", toggleDone);
  $("resetBtn").addEventListener("click", resetCurrentQuestion);
  $("shuffleBtn").addEventListener("click", toggleShuffle);

  // Full Page Modal controls
  $("fullPageOverlayBtn").addEventListener("click", showFullPageModal);
  $("closeModal").addEventListener("click", hideFullPageModal);
  $("fullPageModal").addEventListener("click", (e) => {
    if (e.target === $("fullPageModal")) {
      hideFullPageModal();
    }
  });

  // Initialize list
  updateFilteredList();
  render();
}

function resetIndexAndFilter() {
  state.index = 0;
  state.isShuffled = false;
  state.shuffledIndices = [];
  $("shuffleBtn").classList.remove("active");
  $("shuffleBtn").textContent = "순서 섞기";
  updateFilteredList();
  render();
}

// --- Filtering logic ---
function getFilteredQuestions() {
  // 1. Filter by selected Year & Subject first
  let list = originalQuestions.map((q, idx) => ({ ...q, originalIndex: idx }))
                              .filter(q => q.year === state.year && q.subject === state.subject);

  // 2. Filter by Search Query
  if (state.query) {
    list = list.filter(q => {
      const haystack = `${q.q_num}번 ${q.explanation} ${q.choices.join(" ")}`.toLowerCase();
      return haystack.includes(state.query);
    });
  }

  // 3. Filter by Filter State (all, todo, incorrect)
  if (state.filter === "todo") {
    list = list.filter(q => !state.userAnswers[q.id]);
  } else if (state.filter === "incorrect") {
    list = list.filter(q => state.userAnswers[q.id] && !state.userAnswers[q.id].isCorrect);
  }

  return list;
}

function updateFilteredList() {
  const filtered = getFilteredQuestions();
  
  if (state.isShuffled) {
    // If shuffled, we map using the shuffled indices mapping
    // If size changed, reshuffle
    if (state.shuffledIndices.length !== filtered.length) {
      reshuffle(filtered);
    }
  } else {
    state.filteredList = filtered;
  }
}

function reshuffle(filteredList) {
  const indices = filteredList.map((_, idx) => idx);
  // Fisher-Yates shuffle
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }
  state.shuffledIndices = indices;
  state.filteredList = indices.map(idx => filteredList[idx]);
}

// --- Actions ---
function move(delta) {
  if (!state.filteredList || state.filteredList.length === 0) return;
  state.index = (state.index + delta + state.filteredList.length) % state.filteredList.length;
  render();
}

function toggleDone() {
  const q = state.filteredList[state.index];
  if (!q) return;
  state.done[q.id] = !state.done[q.id];
  localStorage.setItem("exam-study-done", JSON.stringify(state.done));
  render();
}

function resetCurrentQuestion() {
  const q = state.filteredList[state.index];
  if (!q) return;
  delete state.userAnswers[q.id];
  localStorage.setItem("exam-study-answers", JSON.stringify(state.userAnswers));
  render();
}

function toggleShuffle() {
  state.isShuffled = !state.isShuffled;
  const shuffleBtn = $("shuffleBtn");
  
  const filtered = getFilteredQuestions();
  if (state.isShuffled) {
    shuffleBtn.classList.add("active");
    shuffleBtn.textContent = "순서 원래대로";
    reshuffle(filtered);
  } else {
    shuffleBtn.classList.remove("active");
    shuffleBtn.textContent = "순서 섞기";
    state.shuffledIndices = [];
    state.filteredList = filtered;
  }
  state.index = 0;
  render();
}

// --- Interactive Choice Grading ---
function selectChoice(choiceIdx) {
  const q = state.filteredList[state.index];
  if (!q) return;

  // If already answered, do nothing
  if (state.userAnswers[q.id]) return;

  // Grade user's answer
  // Correct answers are represented as array in q.answer (e.g. [4], or [1,4] for multiple keys)
  const isCorrect = q.answer.includes(choiceIdx);
  
  state.userAnswers[q.id] = {
    selected: choiceIdx,
    isCorrect: isCorrect
  };
  
  localStorage.setItem("exam-study-answers", JSON.stringify(state.userAnswers));
  render();
}

// --- Render Functions ---
function renderList() {
  const listContainer = $("questionList");
  listContainer.innerHTML = "";

  if (!state.filteredList || state.filteredList.length === 0) {
    listContainer.innerHTML = `<div class="stat-item" style="grid-column: span 1; width:100%; border:none; color:var(--ink-secondary)">해당하는 문제가 없습니다.</div>`;
    return;
  }

  state.filteredList.forEach((q, idx) => {
    const item = document.createElement("button");
    item.type = "button";
    
    // Set classes based on state
    let classList = "question-item";
    if (idx === state.index) classList += " active";
    
    const ansInfo = state.userAnswers[q.id];
    if (ansInfo) {
      classList += ansInfo.isCorrect ? " solved" : " wrong";
    }
    if (state.done[q.id]) {
      classList += " done";
    }
    item.className = classList;

    item.innerHTML = `
      <span class="q-badge">${q.q_num}</span>
      <div class="q-info">
        <span class="q-title">${q.choices.join(" / ").replace(/[①②③④]/g, "").trim().substring(0, 30)}...</span>
        <span class="q-meta">p.${q.page} · ${ansInfo ? (ansInfo.isCorrect ? "정답" : "오답") : "미풀이"}</span>
      </div>
    `;

    item.addEventListener("click", () => {
      state.index = idx;
      render();
    });

    listContainer.appendChild(item);
  });
}

function renderCurrent() {
  const q = state.filteredList[state.index];
  
  if (!q) {
    $("titleLabel").textContent = "문제를 선택하세요";
    $("positionLabel").textContent = "0 / 0";
    $("yearLabel").textContent = "년도";
    $("subjectLabel").textContent = "과목";
    $("statusLabel").className = "meta-tag status";
    $("statusLabel").textContent = "대기 중";
    $("imageStrip").innerHTML = `<div style="padding: 40px; text-align: center; color: var(--ink-secondary)">왼쪽 목록에서 문제를 선택하여 풀이를 시작하세요.</div>`;
    $("choicesContainer").innerHTML = "";
    $("feedbackBanner").hidden = true;
    $("evidenceBox").hidden = true;
    $("explanationBox").hidden = true;
    return;
  }

  // Header Info
  $("titleLabel").textContent = `${q.q_num}번 문제 학습`;
  $("positionLabel").textContent = `${state.index + 1} / ${state.filteredList.length}`;
  $("yearLabel").textContent = `${q.year}학년도`;
  $("subjectLabel").textContent = q.subject;
  
  // Status tag
  const statusLabel = $("statusLabel");
  const ansInfo = state.userAnswers[q.id];
  if (ansInfo) {
    if (ansInfo.isCorrect) {
      statusLabel.className = "meta-tag status correct";
      statusLabel.textContent = "정답 완료";
    } else {
      statusLabel.className = "meta-tag status wrong";
      statusLabel.textContent = "오답 기록됨";
    }
  } else {
    statusLabel.className = "meta-tag status";
    statusLabel.textContent = "풀이 전";
  }

  // Done button text state
  $("doneBtn").textContent = state.done[q.id] ? "완료 해제" : "완료 표시";
  if (state.done[q.id]) {
    $("doneBtn").classList.add("active");
  } else {
    $("doneBtn").classList.remove("active");
  }

  // Render Images (cropped context block + cropped question block)
  const imageStrip = $("imageStrip");
  imageStrip.innerHTML = "";
  q.images.forEach(imgName => {
    const img = document.createElement("img");
    img.src = `./ocr_images/${imgName}`;
    img.alt = `${q.q_num}번 문제 이미지`;
    imageStrip.appendChild(img);
  });

  // Render choices
  const choicesContainer = $("choicesContainer");
  choicesContainer.innerHTML = "";
  
  const hasAnswered = !!ansInfo;
  
  q.choices.forEach((choiceText, index) => {
    const choiceNum = index + 1;
    const card = document.createElement("button");
    card.type = "button";
    card.className = "choice-card";
    
    // Clean option text of leading numbers or circled numbers if present
    const cleanedText = choiceText.replace(/^[①②③④\s(1)(2)(3)(4)]+/, '').trim();
    
    card.innerHTML = `
      <span class="choice-num">${choiceNum}</span>
      <span class="choice-text">${cleanedText || choiceNum + '번 보기'}</span>
    `;

    // Apply colors post answering
    if (hasAnswered) {
      card.classList.add("disabled");
      
      const isThisCorrect = q.answer.includes(choiceNum);
      const isThisSelected = ansInfo.selected === choiceNum;
      
      if (isThisCorrect) {
        card.classList.add("correct");
      } else if (isThisSelected) {
        card.classList.add("wrong");
      }
    } else {
      card.addEventListener("click", () => selectChoice(choiceNum));
    }

    choicesContainer.appendChild(card);
  });

  // Feedback Banner
  const feedbackBanner = $("feedbackBanner");
  if (hasAnswered) {
    feedbackBanner.hidden = false;
    if (ansInfo.isCorrect) {
      feedbackBanner.className = "feedback-banner correct";
      feedbackBanner.querySelector("#feedbackText").textContent = "정답입니다! 훌륭합니다.";
    } else {
      feedbackBanner.className = "feedback-banner wrong";
      feedbackBanner.querySelector("#feedbackText").textContent = `오답입니다. 정답은 ${q.answer.join(", ")}번 입니다.`;
    }
  } else {
    feedbackBanner.hidden = true;
  }

  // Evidence Box
  const evidenceBox = $("evidenceBox");
  if (hasAnswered && q.evidence) {
    evidenceBox.hidden = false;
    $("evidenceText").textContent = q.evidence;
    if (q.excel_image) {
      $("evidenceImg").src = `./ocr_images/${q.excel_image}`;
      $("evidenceImageContainer").style.display = "block";
    } else {
      $("evidenceImageContainer").style.display = "none";
    }
  } else {
    evidenceBox.hidden = true;
  }

  // Explanation Box
  const explanationBox = $("explanationBox");
  if (hasAnswered) {
    explanationBox.hidden = false;
    $("explanationText").textContent = q.explanation;
  } else {
    explanationBox.hidden = true;
  }
}

function renderStats() {
  const currentSubjectQs = originalQuestions.filter(q => q.year === state.year && q.subject === state.subject);
  $("totalCount").textContent = currentSubjectQs.length;
  
  // Solved Count in current subject
  const currentSolved = currentSubjectQs.filter(q => state.userAnswers[q.id]);
  const currentDone = currentSubjectQs.filter(q => state.done[q.id]);
  
  $("doneCount").textContent = currentDone.length;
  
  // Correct rate
  const correctCount = currentSolved.filter(q => state.userAnswers[q.id].isCorrect).length;
  if (currentSolved.length > 0) {
    const rate = Math.round((correctCount / currentSolved.length) * 100);
    $("correctRate").textContent = `${rate}%`;
  } else {
    $("correctRate").textContent = "0%";
  }
}

function render() {
  renderList();
  renderCurrent();
  renderStats();
}

// --- Overlay Full Page Modal ---
function showFullPageModal() {
  const q = state.filteredList[state.index];
  if (!q) return;
  
  // Format page index like page_001.png
  const pageStr = String(q.page).padStart(3, '0');
  
  // The full page image generated is like "samples/2018_page_1.png" in render_pdf_pages.py or samples/[year]_[subject]_page_[page].png
  // Let's load: samples/[year]_[subject]_page_[page].png
  const fullPageImgPath = `./samples/${q.year}_${q.subject}_page_${q.page}.png`;
  
  $("fullPageImg").src = fullPageImgPath;
  $("fullPageModal").hidden = false;
}

function hideFullPageModal() {
  $("fullPageModal").hidden = true;
}

// Launch application
window.addEventListener("DOMContentLoaded", init);

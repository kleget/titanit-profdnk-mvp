(function () {
  const sectionsNode = document.getElementById("sections");
  const questionsNode = document.getElementById("question-list");
  const formulaNode = document.getElementById("metric-formula-list");
  const addSectionBtn = document.getElementById("add-section");
  const addQuestionBtn = document.getElementById("add-question");
  const addFormulaBtn = document.getElementById("add-metric-formula");

  if (!sectionsNode || !questionsNode || !addSectionBtn || !addQuestionBtn) {
    return;
  }

  function sectionOptions() {
    return [...sectionsNode.querySelectorAll("input[name='section_titles[]']")]
      .map((input) => input.value.trim())
      .filter(Boolean);
  }

  function createSectionInput(value = "") {
    const wrapper = document.createElement("div");
    wrapper.className = "inline-form";
    const input = document.createElement("input");
    input.name = "section_titles[]";
    input.placeholder = "Название секции";
    input.required = true;
    input.value = value;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn small ghost";
    remove.textContent = "Удалить";
    remove.addEventListener("click", () => {
      wrapper.remove();
      syncQuestionSections();
    });
    input.addEventListener("input", syncQuestionSections);

    wrapper.append(input, remove);
    return wrapper;
  }

  function createQuestionItem() {
    const box = document.createElement("div");
    box.className = "question-item";
    box.innerHTML = `
      <div class="inline-form">
        <label>Секция
          <select name="q_section[]"></select>
        </label>
        <label>Тип
          <select name="q_type[]">
            <option value="text">Короткий текст</option>
            <option value="textarea">Большой текст</option>
            <option value="single_choice">Один вариант</option>
            <option value="multiple_choice">Несколько вариантов</option>
            <option value="yes_no">Да / Нет</option>
            <option value="number">Число</option>
            <option value="slider">Слайдер</option>
            <option value="datetime">Дата и время</option>
            <option value="rating">Оценка</option>
          </select>
        </label>
        <label>Обязательный
          <select name="q_required[]">
            <option value="true">Да</option>
            <option value="false">Нет</option>
          </select>
        </label>
      </div>
      <label>Текст вопроса
        <input name="q_text[]" required placeholder="Введите формулировку вопроса">
      </label>
      <label>Опции (для choice): формат "Текст:балл, Текст2:балл"
        <input name="q_options[]" placeholder="Например: Доход:2, Стабильность:1">
      </label>
      <div class="inline-form">
        <label>Минимум
          <input type="number" step="any" name="q_min[]">
        </label>
        <label>Максимум
          <input type="number" step="any" name="q_max[]">
        </label>
        <label>Вес
          <input type="number" step="0.1" name="q_weight[]" value="1">
        </label>
      </div>
      <button type="button" class="btn small ghost remove-question">Удалить вопрос</button>
    `;

    const removeBtn = box.querySelector(".remove-question");
    removeBtn.addEventListener("click", () => box.remove());
    return box;
  }

  function createFormulaItem() {
    const box = document.createElement("div");
    box.className = "question-item";
    box.innerHTML = `
      <div class="inline-form">
        <label>Ключ метрики
          <input name="metric_key[]" placeholder="adaptability_index">
        </label>
        <label>Название
          <input name="metric_label[]" placeholder="Индекс адаптивности">
        </label>
      </div>
      <label>Формула
        <input name="metric_expression[]" placeholder="round((digital_skill + stress_level) / 2, 2)">
      </label>
      <label>Описание
        <input name="metric_description[]" placeholder="Что показывает метрика">
      </label>
      <button type="button" class="btn small ghost remove-formula">Удалить формулу</button>
    `;

    const removeBtn = box.querySelector(".remove-formula");
    removeBtn.addEventListener("click", () => box.remove());
    return box;
  }

  function syncQuestionSections() {
    const values = sectionOptions();
    questionsNode.querySelectorAll("select[name='q_section[]']").forEach((select) => {
      const current = select.value;
      select.innerHTML = "";
      (values.length ? values : ["Общая секция"]).forEach((item) => {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        select.appendChild(option);
      });
      if ([...select.options].some((opt) => opt.value === current)) {
        select.value = current;
      }
    });
  }

  addSectionBtn.addEventListener("click", () => {
    sectionsNode.appendChild(createSectionInput());
    syncQuestionSections();
  });

  addQuestionBtn.addEventListener("click", () => {
    questionsNode.appendChild(createQuestionItem());
    syncQuestionSections();
  });

  if (addFormulaBtn && formulaNode) {
    addFormulaBtn.addEventListener("click", () => {
      formulaNode.appendChild(createFormulaItem());
    });
  }

  if (!questionsNode.children.length) {
    questionsNode.appendChild(createQuestionItem());
  }

  if (formulaNode && !formulaNode.children.length) {
    const sample = createFormulaItem();
    sample.querySelector("input[name='metric_key[]']").value = "adaptability_index";
    sample.querySelector("input[name='metric_label[]']").value = "Индекс адаптивности";
    sample.querySelector("input[name='metric_expression[]']").value =
      "round((digital_skill + stress_level) / 2, 2)";
    sample.querySelector("input[name='metric_description[]']").value =
      "Средняя оценка цифровых навыков и устойчивости к нагрузке";
    formulaNode.appendChild(sample);
  }

  syncQuestionSections();
})();

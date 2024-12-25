# Application Intents

i'll add more to this page later

### Intent Calculator

<!-- i do not know javascript or html or css -->
<div class="intent-calculator">
  <div class="intent-grid">
    <div v-for="section in sections" :key="section" class="intent-section">
      <div class="intent-rows">
        <div class="intent-row">
          <label v-for="name in getSectionIntents(section)" :key="name">
            <input type="checkbox" 
                   v-model="selected[name]" 
                   @change="calculateValue"
                   :disabled="name.endsWith('$EVENTS') && !selected[`${section}$READ`]">
            {{ formatIntentName(name) }}
          </label>
        </div>
      </div>
    </div>
    <div class="intent-section">
      <div class="section-title">The following intents require specific verification:</div>
      <div class="intent-rows">
        <div class="intent-row">
          <label v-for="name in ['MEMBERS$USERPROXY_TOKEN$READ', 'MEMBERS$USERPROXY_TOKEN$WRITE']" :key="name">
            <input type="checkbox" v-model="selected[name]" @change="calculateValue">
            {{ formatIntentName(name) }}
          </label>
        </div>
      </div>
    </div>
  </div>

  <div class="intent-value">
    <strong>Intent Value:</strong> {{ sum }}
  </div>
</div>

<script setup>
import { ref, watch, computed } from 'vue'

const intents = {
  MEMBERS$READ: 1 << 0,
  MEMBERS$WRITE: 1 << 1,
  MEMBERS$EVENTS: 1 << 2,
  GROUPS$READ: 1 << 3,
  GROUPS$WRITE: 1 << 4,
  GROUPS$EVENTS: 1 << 5,
  LATCH$READ: 1 << 6,
  LATCH$WRITE: 1 << 7,
  LATCH$EVENTS: 1 << 8,
  MESSAGES$READ: 1 << 9,
  MESSAGES$WRITE: 1 << 10,
  MESSAGES$EVENTS: 1 << 11,
  MEMBERS$USERPROXY_TOKEN$READ: 1 << 12,
  MEMBERS$USERPROXY_TOKEN$WRITE: 1 << 13,
}

const selected = ref(Object.keys(intents).reduce((acc, key) => {
  acc[key] = false
  return acc
}, {}))

const sections = computed(() => {
  return [...new Set(
    Object.keys(intents)
      .filter(name => !name.includes('USERPROXY_TOKEN'))
      .map(name => name.split('$')[0])
  )]
})

const getSectionIntents = (section) => {
  return Object.keys(intents)
    .filter(name => name.startsWith(section) && !name.includes('USERPROXY_TOKEN'))
    .sort((a, b) => {
      const order = { READ: 1, WRITE: 2, EVENTS: 3 }
      const aType = a.split('$').pop()
      const bType = b.split('$').pop()
      return order[aType] - order[bType]
    })
}


watch(selected.value, (newVal, oldVal) => {
  sections.value.forEach(section => {
    if (!newVal[`${section}$READ`] && selected.value[`${section}$EVENTS`]) {
      selected.value[`${section}$EVENTS`] = false
      calculateValue()
    }
  })
}, { deep: true })

const formatIntentName = (name) => {
    return name.toLowerCase().replaceAll('$', '.')
}

    const sum = ref(0)

const calculateValue = () => {
  sum.value = Object.entries(selected.value)
    .reduce((acc, [name, isSelected]) => {
      return acc + (isSelected ? intents[name] : 0)
    }, 0)
}
</script>

<style>
.intent-calculator {
  padding: 1rem;
  border: 1px solid #eaecef;
  border-radius: 4px;
  margin: 1rem 0;
}

.intent-grid {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.intent-section {
  padding: 0rem 0;
}

.section-title {
  font-weight: bold;
  padding-top: 0.5rem;
  padding-bottom: 0.25rem;
}

.intent-rows {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.intent-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.intent-row label {
  display: flex;
  align-items: center;
  min-width: 200px;
  cursor: pointer;
  padding: 0.25rem 0;
}

.intent-row input[type="checkbox"] {
  width: 1.5em;
  height: 1.5em;
  margin-right: 0.5em;
  vertical-align: middle;
  cursor: pointer;
}

.intent-row input[type="checkbox"]:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.intent-row label:has(input:disabled) {
  cursor: not-allowed;
  opacity: 0.5;
}

.intent-value {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eaecef;
}
</style>

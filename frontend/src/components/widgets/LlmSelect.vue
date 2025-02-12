<script setup>
import Dropdown from 'primevue/dropdown';

import { httpClient } from "../../api/httpClient"

</script>

<script>

export default {
  inject: ["eventBus"],
  props: ['modelValue', "tooltip", "show_default_option", "placeholder"],
  emits: ['update:modelValue'],
  data() {
    return {
      available_llm_models: [],
    }
  },
  computed: {
    selected_llm: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    }
  },
  mounted() {
    this.selected_llm = this.modelValue
    this.get_available_llm_models()
  },
  watch: {
  },
  methods: {
    get_available_llm_models() {
      httpClient.get(`/api/v1/columns/available_llm_models`)
      .then((response) => {
        this.available_llm_models = response.data
        if (this.show_default_option) {
          this.available_llm_models.unshift({model_id: null, verbose_name: "Default"})
        }
        if (!this.selected_llm && this.available_llm_models.length > 0) {
          this.selected_llm = this.available_llm_models[0].code
        }
      })
    },
  },
}
</script>


<template>
  <div>
    <Dropdown v-model="selected_llm" :options="available_llm_models" optionLabel="verbose_name" optionValue="model_id"
      :placeholder="placeholder || 'Select LLM...'" v-tooltip.bottom="{ value: tooltip, showDelay: 400 }"
      class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
  </div>
</template>

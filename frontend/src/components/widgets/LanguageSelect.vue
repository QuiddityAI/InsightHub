<script setup>
import { useToast } from 'primevue/usetoast';
import { languages } from "../../utils/utils"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ['modelValue', "available_language_codes", "offer_wildcard", "tooltip", "use_last_used_language"],
  emits: ['update:modelValue'],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    available_languages() {
      let filtered_languages = []
      if (this.available_language_codes?.length > 0) {
        filtered_languages = this.available_language_codes.map(code => languages.find(lang => lang.code == code))
      } else {
        filtered_languages = languages
      }
      if (this.offer_wildcard) {
        const any_language = [{ name: 'any', code: null, flag: '🌍' }]
        filtered_languages = any_language.concat(filtered_languages)
      }
      return filtered_languages
    },
    selected_language: {
      get() {
        return this.modelValue
      },
      set(value) {
        if (this.use_last_used_language) {
          this.appStateStore.last_used_language = value
        }
        this.$emit('update:modelValue', value)
      }
    }
  },
  mounted() {
    if (this.modelValue) {
      this.selected_language = this.modelValue
    } else if (this.use_last_used_language) {
      this.selected_language = this.appStateStore.last_used_language
    } else if (this.available_languages.length > 0) {
      this.selected_language = this.available_languages[0].code
    } else {
      this.selected_language = null
    }
  },
  watch: {
  },
  methods: {
  },
}
</script>


<template>
  <div>
    <select v-model="selected_language" class="w-18 appearance-none ring-0 border-0 bg-transparent"
      v-tooltip.bottom="{ value: tooltip, showDelay: 400 }">
      <option v-for="language in available_languages" :value="language.code">{{ language.flag }}</option>
    </select>
  </div>
</template>

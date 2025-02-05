<script setup>
import {
  ChevronLeftIcon,
  ChevronRightIcon,
 } from "@heroicons/vue/24/outline"

import BorderlessButton from '../widgets/BorderlessButton.vue';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"

const appState = useAppStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ['highlights', "dataset_id"],
  data() {
    return {
      highlight_index: 0,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    highlight() {
      return this.highlights[this.highlight_index]
    },
  },
  mounted() {
  },
  watch: {
    highlights(val, oldVal) {
      this.highlight_index = 0
    },
  },
  methods: {
  },
}
</script>


<template>
  <div class="border-l-4 px-2 flex flex-col gap-1 pb-1" v-if="highlights.length">
    <div class="flex flex-row items-center">
      <div class="font-semibold text-gray-500 text-xs">Part from
        {{ appState.datasets[dataset_id].schema.object_fields[highlight.field]?.name || appState.datasets[dataset_id].schema.object_fields[highlight.field]?.identifier }}
        <span class="text-gray-400 text-xs">(with relevant keywords)</span>
      </div>
      <div class="flex-1"></div>
      <div v-if="highlights.length > 1" class="flex flex-row">
        <BorderlessButton
          @click="highlight_index = (highlight_index - 1 + highlights.length) % highlights.length">
          <ChevronLeftIcon class="h-3 w-3" />
        </BorderlessButton>
        <span class="text-gray-400 text-xs font-bold">
          {{ highlight_index + 1 }} / {{ highlights.length }}
        </span>
        <BorderlessButton
          @click="highlight_index = (highlight_index + 1) % highlights.length">
          <ChevronRightIcon class="h-3 w-3" />
        </BorderlessButton>
      </div>
    </div>
    <div class="mt-1 text-gray-700 text-xs break-words" v-html="highlight.value"></div>
  </div>
</template>
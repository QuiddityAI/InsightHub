<script setup>
import {
  ChevronLeftIcon,
  ChevronRightIcon,
 } from "@heroicons/vue/24/outline"

import BorderlessButton from '../widgets/BorderlessButton.vue';
import ExpandableTextArea from "../widgets/ExpandableTextArea.vue";

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { highlight_words_in_text } from "../../utils/utils"

const appState = useAppStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ['highlights', "item", "rendering"],
  data() {
    return {
      highlight_index: 0,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    relevant_chunk() {
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
  <div class="border-l-4 px-2 flex flex-col gap-1 pb-1" v-if="highlights.length && relevant_chunk.value && item._dataset_id">
    <div class="flex flex-row items-center">
      <div class="font-semibold text-gray-500 text-xs">Part in
        {{ appState.datasets[item._dataset_id].schema.object_fields[relevant_chunk.field]?.name }}{{ relevant_chunk.value?.page ? `, Page ${relevant_chunk.value.page}` : "" }}
        <span class="text-gray-400">(AI relevance)</span>
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
    <ExpandableTextArea class="mt-1 text-gray-700 text-xs break-words" :max_lines="12"
      :html_content="highlight_words_in_text(relevant_chunk.value.text, appState.selected_document_query.split(' '))">
    </ExpandableTextArea>

    <a v-if="rendering.full_text_pdf_url && rendering.full_text_pdf_url(item)"
      :href="`${rendering.full_text_pdf_url(item)}#page=${relevant_chunk.value.page}`" target="_blank"
      class="mt-1 text-gray-500 text-xs">Open PDF at this page</a>
  </div>
</template>

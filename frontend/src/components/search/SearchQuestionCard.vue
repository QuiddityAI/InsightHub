<script setup>
import { useToast } from 'primevue/usetoast';

import OverlayPanel from 'primevue/overlaypanel';

import CollectionItem from '../collections/CollectionItem.vue';

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    list_of_text_and_citation_parts(text) {
      text.replace(/(?:\r\n|\r|\n)/g, '<br>')
      text = text.replaceAll("; ", "] [")
      const regex = /\[([0-9]+), "?([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})"?\]/ig;

      let i = 1
      const citations = []
      for (const matches of text.matchAll(regex)) {
        const whole_match = matches[0]
        const dataset_id = parseInt(matches[1])
        const item_id = matches[2]
        const replacement = " <split> "
        text = text.replace(whole_match, replacement)
        citations.push({
          is_citation: true,
          citation_index: i,
          dataset_id: dataset_id,
          item_id: item_id,
        })
        i++
      }
      const text_array = text.split(" <split> ")
      const interleaved_array = []
      for (const [index, item] of text_array.entries()) {
        interleaved_array.push({
          is_citation: false,
          content: item,
        })
        if (citations[index]) {
          interleaved_array.push(citations[index])
        }
      }
      return interleaved_array
    },
  },
}
</script>

<template>
  <div class="mt-3 p-3 rounded bg-gray-100/50">
    <div class="flex flex-col gap-2">
      <div class="flex flex-row">
        <span class="text-md font-bold">{{ mapState.map_parameters?.search.question }}</span>
        <div class="flex-1"></div>
        <span class="text-gray-400 text-sm">AI Generated</span>
      </div>

      <div v-if="mapState.answer?.answer">
        <span v-for="part in list_of_text_and_citation_parts(mapState.answer.answer)">
          <span v-if="part.is_citation">
            <button
              @click="(event) => { selected_citation = part; $refs.citation_tooltip.toggle(event) }"
              title="Click to show reference"
              class="text-blue-500 cursor-pointer"
              type="button">
              [{{ part.citation_index }}]
            </button>
          </span>
          <span v-else v-html="part.content">
          </span>
        </span>
      </div>

      <div v-if="!mapState.answer?.answer" class="text-gray-400 text-md">
        Loading...
      </div>

    </div>

    <OverlayPanel ref="citation_tooltip">
      <CollectionItem
        class="w-[500px]"
        :dataset_id="selected_citation.dataset_id"
        :item_id="selected_citation.item_id">
      </CollectionItem>
    </OverlayPanel>

  </div>

</template>

<style scoped>
</style>

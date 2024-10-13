<script setup>

import { PaperAirplaneIcon } from "@heroicons/vue/24/outline"

import { marked } from "marked";

import { useToast } from 'primevue/usetoast';

import { httpClient, djangoClient } from "../../api/httpClient"
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
  inject: [],
  props: [],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-col gap-5 py-7 px-10">
    <div class="flex flex-row items-center gap-3">
      <h3 class="font-bold text-[15px]">
        Explanation
      </h3>
    </div>

    <ul class="flex flex-col gap-5">
      <li v-for="explanation in collectionStore.collection.explanation_log"
        class="list-disc ml-5 text-gray-600" v-html="marked.parse(explanation.explanation)">
      </li>
    </ul>

    <div v-if="collectionStore.collection.explanation_log.length === 0">
      <Message severity="info">
        No explanations available yet
      </Message>
    </div>
  </div>

</template>

<style scoped>
</style>

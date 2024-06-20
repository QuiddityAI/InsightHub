<script setup>
import { useToast } from 'primevue/usetoast';

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
  props: ["chat_data"],
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
  },
}
</script>

<template>
  <div class="rounded-xl border px-3 py-2">

    <div v-if="!chat_data.collection" class="flex flex-row gap-3 items-center">
      <h3 class="text-gray-400 font-semibold">Context:</h3>
      <span class="text-gray-400">Any item in</span>
      <span v-for="dataset_id in chat_data.search_settings?.dataset_ids"
       class="mr-3 rounded-xl bg-gray-100 px-2 py-[2px] text-sm text-gray-400">
        {{ appState.datasets[dataset_id]?.name }}
      </span>
    </div>

  </div>

</template>

<style scoped>
</style>

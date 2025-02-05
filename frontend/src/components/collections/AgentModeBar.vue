<script setup>
import {
  NoSymbolIcon,
} from "@heroicons/vue/24/outline"

import ProgressSpinner from "primevue/progressspinner";

import BorderlessButton from "../widgets/BorderlessButton.vue";

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store';
import { httpClient } from "../../api/httpClient"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()

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
  <div class="w-full px-5 py-1 flex flex-row items-center gap-4">
    <span class="text-orange-500">{{ $t('AgentModeBar.processing') }}</span>
    <ProgressSpinner class="w-5 h-5 -mr-1" />
    <span class="text-gray-700">
      {{ collectionStore.collection.current_agent_step }}
    </span>
    <div class="flex-1"></div>
    <BorderlessButton @click="collectionStore.cancel_agent" class="py-1">
      <NoSymbolIcon class="h-5 w-5 inline" /> {{ $t('AgentModeBar.cancel') }}
    </BorderlessButton>
  </div>
</template>

<style scoped>
</style>

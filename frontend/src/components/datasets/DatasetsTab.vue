<script setup>
import {
  CursorArrowRaysIcon,
  RectangleGroupIcon,
  PlusIcon,
  MinusIcon,
  ViewfinderCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline"

import Toast from 'primevue/toast';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import DynamicDialog from 'primevue/dynamicdialog'
import OverlayPanel from "primevue/overlaypanel";
import Message from 'primevue/message';

import DatasetsArea from "../datasets/DatasetsArea.vue"

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
  props: [],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    use_single_column() {
      return window.innerWidth < 768 || (this.selected_tab === "results" && this.appStateStore.search_result_ids.length === 0)
    },
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
  <div class="mt-3 mb-3 p-4 shadow-sm rounded-md flex flex-row items-center justify-center bg-white">

    <Message v-if="!appState.logged_in" :closable="false">
      Log in to upload your own files (PDF, CSV, txt, etc.) to make them searchable and process them using AI.
    </Message>

    <DatasetsArea v-if="appState.logged_in"
      class="h-full min-w-[600px]">
    </DatasetsArea>

  </div>

</template>

<style scoped>
</style>

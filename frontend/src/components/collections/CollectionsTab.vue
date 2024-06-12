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

import SearchArea from "../search/SearchArea.vue"
import FilterList from "../search/FilterList.vue"
import RangeFilterList from "../search/RangeFilterList.vue"
import ResultList from "../search/ResultList.vue"
import ObjectDetailsModal from "../search/ObjectDetailsModal.vue"
import CollectionArea from "../collections/CollectionArea.vue"
import CollectionItem from "../collections/CollectionItem.vue"
import StatisticList from "../search/StatisticList.vue"
import DatasetsArea from "../datasets/DatasetsArea.vue"
import ChatList from "../chats/ChatList.vue"

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
  <div class="mt-3 mb-3 shadow-sm rounded-md flex flex-row items-center justify-center bg-white">

    <CollectionArea></CollectionArea>

  </div>

</template>

<style scoped>
</style>

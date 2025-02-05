<script setup>
import {
  HomeIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store";

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      internal_organization_id: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.internal_organization_id = this.appStateStore.organization_id
  },
  watch: {
    "appStateStore.organization_id": function (newValue, oldValue) {
      // using internal variable to be able to reset parameters before
      // actually changing global dataset_id in select-field listener below
      this.internal_organization_id = this.appStateStore.organization_id
    },
  },
  methods: {
    organization_id_changed_by_user() {
      this.appStateStore.set_organization_id(this.internal_organization_id)
    },
  },
}
</script>


<template>
  <div class="flex-none flex flex-row items-center gap-1">

    <a
      v-tooltip.right="{ value: 'Reset search', showDelay: 400 }"
      :href="`?organization_id=${appState.organization_id}`"
      class="w-5 h-5 rounded p-[2px] text-gray-400 hover:bg-gray-100">
      <HomeIcon></HomeIcon>
    </a>

    <div class="flex-1"
      v-tooltip.bottom="{ value: $t('TopMenu.select-the-organization'), showDelay: 400 }">
      <select
        v-model="internal_organization_id"
        @change="organization_id_changed_by_user"
        class="w-full rounded-md border-none pb-0 pl-2 pr-8 pt-0 text-[13px] font-thin text-gray-500 font-[Lexend]">
        <option v-for="item in appState.available_organizations" :value="item.id" selected>
          {{ item.name }}
        </option>
      </select>
    </div>

  </div>

</template>

<style scoped>
</style>

<script setup>
import {
  ChevronRightIcon,
} from "@heroicons/vue/24/outline"

import OrganizationSelect from "../general/OrganizationSelect.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>
export default {
  props: [],
  emits: [],
  data() {
    return {}
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collapsed() {
      return this.collectionStore.collection_id !== null
    },
  },
  mounted() {},
  methods: {
    open_new_collection_dialog() {
      this.collectionStore.close_collection()
    },
  },
}
</script>

<template>
  <div class="h-full w-[250px] transition-[margin] duration-300 shadow-md bg-white flex flex-col" :class="{
      '-ml-[250px]': collapsed,
      'ml-0': !collapsed,
    }">

    <div class="flex-1 overflow-y-auto flex flex-col gap-3 pt-3 pb-3 pl-3 pr-3">

      <OrganizationSelect class="ml-2"></OrganizationSelect>

      <button v-if="appState.organization?.schemas_for_user_created_datasets?.length > 0"
        class="py-1 text-sm text-gray-500 text-left pl-3 border border-gray-200 rounded-lg hover:border-blue-300 hover:text-blue-500"
        @click="appState.set_app_tab('datasets')">
        + {{ $t('TopMenu.upload-files') }}
      </button>

      <div class="flex flex-row items-center text-left px-2 mt-1">
        <h3 class="font-bold text-[12px] text-gray-500">
          {{ $t('CollectionList.recent-collections') }}
        </h3>
      </div>

      <div v-for="collection in collectionStore.available_collections" :key="collection.id" class="">
        <button
          class="w-full text-left text-[15px] text-md font-normal text-gray-700 pl-1 pr-2 py-1 flex flex-row gap-[6px] items-center rounded-md hover:text-blue-500 hover:bg-gray-100"
          @click="collectionStore.open_collection(collection.id, collection.actual_classes[0].name)">
          <span>
            <ChevronRightIcon class="w-3 h-3 text-gray-500"></ChevronRightIcon>
          </span>
          <h3 class="flex-initial min-w-0 break-words">
            {{ collection.name }}
          </h3>
        </button>
      </div>

      <div v-if="appState.logged_in && collectionStore.available_collections.length === 0">
        <h3 class="font-normal text-[15px] text-center text-gray-500">
          {{ $t('CollectionList.no-collections-yet') }}
        </h3>
      </div>

      <div v-if="!appState.logged_in">
        <h3 class="font-normal text-[15px] text-center text-gray-500">
          {{ $t('CollectionList.log-in-to-use-collections') }}
        </h3>
      </div>

    </div>

  </div>
</template>

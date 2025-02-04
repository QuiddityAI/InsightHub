<script setup>

import { useToast } from 'primevue/usetoast';

import SearchTaskListItem from './SearchTaskListItem.vue';
import BorderButton from '../widgets/BorderButton.vue';

import { debounce } from '../../utils/utils';
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
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
      commit_notification_emails_debounce: debounce(() => {
        collectionStore.commit_notification_emails()
      }, 1000),
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.collectionStore.fetch_saved_search_tasks()
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-col gap-5 px-10">
    <div class="flex flex-row items-center gap-3">
      <h3 class="font-bold text-[15px]">
        Saved / Periodic Searches
      </h3>
    </div>

    <div class="flex flex-row items-center gap-3">
      <input class="flex-1 px-2 border border-gray-200 rounded-md text-sm"
        placeholder="E-Mail addresses to notify for new items (comma separated)"
        v-model="collectionStore.collection.notification_emails"
        @change="commit_notification_emails_debounce">
      <BorderButton class="h-full" v-if="appState.dev_mode"
        @click="collectionStore.test_notification_email({run_on_current_candidates: false})">
        Send test e-Mail
      </BorderButton>
      <BorderButton class="h-full" v-if="appState.dev_mode"
        @click="collectionStore.test_notification_email({run_on_current_candidates: true})">
        Test periodic searches on current candidates
      </BorderButton>
    </div>

    <ul class="flex flex-col gap-5">
      <SearchTaskListItem v-for="task in collectionStore.saved_search_tasks"
        :task="task">
      </SearchTaskListItem>
    </ul>

    <div v-if="collectionStore.saved_search_tasks.length === 0">
      <div class="text-gray-400 ml-3 -mt-3">
        No saved searches yet
      </div>
    </div>
  </div>

</template>

<style scoped>
</style>
